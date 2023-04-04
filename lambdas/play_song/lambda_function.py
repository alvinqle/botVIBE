import json
import os

from nacl.signing import VerifyKey
from nacl.exceptions import BadSignatureError

from helpers.bot_client import run_bot
from helpers.dynamodb_client import check_session, update_session

DISCORD_PUBLIC_KEY = os.environ['DISCORD_PUBLIC_KEY']


def lambda_handler(event, context):
    try:
        body = json.loads(event['body'])
        signature = event['headers']['x-signature-ed25519']
        timestamp = event['headers']['x-signature-timestamp']

        # validate the interaction
        verify_key = VerifyKey(bytes.fromhex(DISCORD_PUBLIC_KEY))
        message = timestamp + json.dumps(body, separators=(',', ':'))

        try:
            verify_key.verify(message.encode(), signature=bytes.fromhex(signature))
        except BadSignatureError:
            return {
                'statusCode': 401,
                'body': json.dumps('invalid request signature')
            }

        # handle the interaction
        t = body['type']
        if t == 1:
            return {
                'statusCode': 200,
                'body': json.dumps({
                    'type': 1
                })
            }
        elif t == 2:
            return command_handler(body)
        else:
            return {
                'statusCode': 400,
                'body': json.dumps('unhandled request type')
            }
    except Exception as e:
        return {
            'statusCode': 400,
            'body': json.dumps(e)
        }


def command_handler(body):
    command = body['data']['name']

    if command == 'botvibe':
        is_bot_active = check_session(bot_name='botVIBE')
        if is_bot_active:
            return {
                'statusCode': 200,
                'body': json.dumps("botVIBE is already running. Have it !join the channel you're currently in.")
            }
        else:
            print('Starting botVIBE...')
            update_session(bot_name='botVIBE', active=True)
            run_bot()
    else:
        return {
            'statusCode': 400,
            'body': json.dumps('Unhandled command')
        }
