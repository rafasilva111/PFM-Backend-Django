import concurrent.futures
from apps.etl_app.functions import (
    check_if_task_stopped,
)

def transform(
    logger,
    task,
    threads,
    *,
    extract_model,
    transform_model,
    transform_instance_fn,
    get_instances_to_delete_fn,
    get_instances_to_process_fn,
    offset=None,
    process_name="item",
    print_start_header=None,
    print_end_header=None,
):
    """
    Generic transformation function for ETL processes.

    Args:
        logger (logging.Logger): Logger instance.
        task (Task): Task object.
        threads (int): Number of threads.
        extract_model: Source model (extraction DB).
        transform_model: Target model (transform DB).
        transform_instance_fn: Function to transform a single instance.
        process_name (str): Name of the process (for logging).
        print_start_header (callable): Function to print start header.
        print_end_header (callable): Function to print end header.
        get_offset_fn (callable): Function to compute stopping offset.
        get_instances_to_delete_fn (callable): Function to get instances to delete on resume.
        get_instances_to_process_fn (callable): Function to get instances to process.

    Returns:
        Tuple[Task, bool]: Updated task and completion status.
    """

    total_processed = 0
    completed = False
    stopping_condition_triggered = False

    # Print start header
    if print_start_header:
        print_start_header(logger, f"Starting {process_name.capitalize()} Transformation")


    # === STEP 2: CLEANUP ON RESUME =============================================
    if task.step != 0 and get_instances_to_delete_fn:
        instances_to_delete = get_instances_to_delete_fn(transform_model, task)
        for obj in instances_to_delete:
            if hasattr(obj, 'tags'):
                obj.tags.clear()
        transform_model.delete().where(transform_model.id > task.step).execute()

    # === STEP 3: RETRIEVE INSTANCES TO PROCESS =================================
    instances_to_process = get_instances_to_process_fn(extract_model, task)
    total_instances = instances_to_process.count()
    if total_instances == 0:
        logger.info(f"No {process_name}s found to transform.")
        return task, True

    logger.info(f"Found {total_instances} {process_name}s to transform.\n")

    # === STEP 4: PROCESS IN PARALLEL ===========================================
    with concurrent.futures.ThreadPoolExecutor(max_workers=threads) as executor:
        futures = []
        for instance in instances_to_process:
            if check_if_task_stopped(task):
                logger.info("Stop signal detected — no new transformation tasks will be submitted.")
                break
            futures.append(executor.submit(transform_instance_fn, logger, task, instance, offset))

        try:
            for future in concurrent.futures.as_completed(futures):
                if check_if_task_stopped(task):
                    logger.info("Stop signal detected — waiting for running transformation threads to finish...")
                    break
                try:
                    result, stopping_condition_triggered = future.result()
                except Exception as e:
                    logger.error(f"Future raised an exception: {e}", exc_info=True)
                    continue

                if result:
                    total_processed += 1
                    task.step += 1
                    task.items_processed += 1
                    task.save()

                if stopping_condition_triggered:
                    logger.info("Stopping condition triggered during transformation.")
                    break
        finally:
            executor.shutdown(wait=True, cancel_futures=True)
            if not (stopping_condition_triggered or check_if_task_stopped(task)):
                completed = True

    # Print end header
    if print_end_header:
        print_end_header(logger, f"{process_name.capitalize()} Transformation Completed")

    return task, completed
