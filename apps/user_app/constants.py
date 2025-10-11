from apps.user_app.models import User

# Define groups and their permissions
GROUPS_PERMISSIONS = {
    User.UserType.PLACEHOLDER: [
    ],
    User.UserType.COMPANY: [
    ],
    User.UserType.NORMAL: [
    ],
    User.UserType.PREMIUM: [
    ],
    User.UserType.COMPANY_STAFF: [
        # User permissions
        "can_view_user","can_view_users",
        # Recipe permissions
        "can_view_recipe","can_view_recipes", "can_edit_recipe",
        # Recipe Report permissions
        "can_view_recipe_report", "can_view_recipe_reports"
    ],
    User.UserType.COMPANY_ADMIN: [
        # User permissions
        "can_view_user","can_view_users",
        # Recipe permissions
        "can_view_recipe","can_view_recipes", "can_edit_recipe",
        # Recipe Audit Log permissions
        "can_view_audit_log", "can_view_audit_logs",
        # Recipe Report permissions
        "can_view_recipe_report", "can_view_recipe_reports"
    ],
    User.UserType.APP_STAFF: [
        # User permissions
        "can_view_user","can_view_users","can_invite_user","can_edit_user","can_delete_user","can_disable_user",
        # Task permissions
        "can_view_task","can_view_tasks","can_restart_task", "can_cancel_task", "can_pause_task", "can_resume_task",
        # Job permissions
        "can_view_job","can_view_jobs", "can_pause_job", "can_resume_job" ,
        # Recipe permissions
        "can_view_recipe","can_view_recipes", "can_edit_recipe", "can_verify_recipe",
        # Recipe Audit Log permissions
        "can_view_audit_log", "can_view_audit_logs", "can_accept_audit_log", "can_unaccept_audit_log", "can_review_audit_log", "can_unreview_audit_log",
        # Recipe Report permissions
        "can_view_recipe_report", "can_view_recipe_reports", "can_create_recipe_report", "can_review_recipe_report", "can_unreview_recipe_report"
    ],
    User.UserType.APP_ADMIN: [
        # User permissions
        "can_view_user","can_view_users","can_invite_user","can_edit_user","can_delete_user","can_disable_user",
        # Company permissions
        "can_view_company","can_view_companies","can_create_company","can_edit_company","can_delete_company",
        # Invite permissions
        "can_view_invite","can_view_invites","can_edit_invite","can_delete_invite",
        # Task permissions
        "can_view_task","can_view_tasks","can_restart_task", "can_cancel_task", "can_create_task","can_edit_task","can_delete_task", "can_pause_task", "can_resume_task",
        # Job permissions
        "can_view_job","can_view_jobs", "can_create_job","can_edit_job","can_delete_job", "can_pause_job", "can_resume_job",
        # Recipe permissions
        "can_view_recipe","can_view_recipes", "can_edit_recipe", "can_delete_recipe", "can_verify_recipe",
        # Recipe Audit Log permissions
        "can_view_audit_log", "can_view_audit_logs", "can_delete_audit_log", "can_accept_audit_log", "can_unaccept_audit_log", "can_review_audit_log", "can_unreview_audit_log",
         # Recipe Report permissions
        "can_view_recipe_report", "can_view_recipe_reports", "can_create_recipe_report", "can_delete_recipe_report", "can_review_recipe_report", "can_unreview_recipe_report"
    ],
}

"""

    Constraints

"""

REGISTER_MINIMUM_AGE = 12

USER_MIN_WEIGHT = 50
USER_MAX_WEIGHT = 200

USER_MIN_HEIGHT = 120
USER_MAX_HEIGHT = 300


"""

    Strings

"""

" User constraints errors "

STRING_USER_BIRTHDATE_PAST_ERROR = "Birth date must be in the past."
STRING_USER_BIRTHDATE_YOUNG_ERROR = "You must be at least 16 years old."


"""

    Values

"""

NORMAL_WEIGHT_BMI_LOWER_LIMIT = 18.5
NORMAL_WEIGHT_BMI_UPPER_LIMIT = 24.9



