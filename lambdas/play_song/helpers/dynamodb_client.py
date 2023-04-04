import boto3

dynamodb = boto3.resource('dynamodb')


def check_session(bot_name: str) -> bool:
    table = dynamodb.Table('bot_sessions')
    response = table.get_item(
        Key={
            'name': bot_name,
        }
    )
    item = response['Item']
    return item['is_active']


def update_session(bot_name: str, active: bool, session_id: str = None) -> bool:
    try:
        table = dynamodb.Table('bot_sessions')
        table.update_item(
            Key={
                'name': bot_name,
            },
            UpdateExpression='SET session_id = :val1, is_active = :val2',
            ExpressionAttributeValues={
                ':val1': session_id,
                ':val2': active,
            }
        )
        return True
    except Exception as e:
        return False
