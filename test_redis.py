import redis

# Connect to Redis (make sure the host and port match your Django settings)
r = redis.StrictRedis(host='192.168.96.2', port=6379, db=0, decode_responses=True)

# Group name to check
group_name = "test"  # Replace with your actual group name

# Redis key for the group
group_key = f'channel_layer.group:{group_name}'

# Get the members of the group (it will return a set of channels)
members = r.smembers(group_key)

# Print the members (channel names)
for member in members:
    print(f"Member: {member}")