import os
import requests
from flask import Flask, jsonify, request, send_from_directory

app = Flask(__name__, static_folder='static')

BOT_TOKEN = os.environ.get('BOT_TOKEN', 'YOUR_BOT_TOKEN')
ADMIN_CHAT_ID = os.environ.get('ADMIN_CHAT_ID', 'YOUR_ADMIN_CHAT_ID')

db = {
    "products": [
        {
            "id": 1,
            "title": "VIP Video Vault - Full Access",
            "price": "99",
            "description": "Instant access to all private videos and updates.",
            "link": "https://t.me/+YourGroupInviteLink",
        }
    ],
    "orders": [],
    "config": {"upi_id": "yourname@okhdfcbank"},
}


@app.route('/')
def index():
  return send_from_directory('static', 'index.html')


@app.route('/api/data')
def get_data():
  return jsonify(db)


@app.route('/api/order/submit', methods=['POST'])
def submit_order():
  data = request.json
  order_id = len(db['orders']) + 1
  data['id'] = order_id
  data['status'] = 'pending'
  db['orders'].append(data)

  if BOT_TOKEN != 'YOUR_BOT_TOKEN' and ADMIN_CHAT_ID != 'YOUR_ADMIN_CHAT_ID':
    msg = (
        f"🚨 *New VIP Order Received!*\n\n📦 Product ID:"
        f" {data.get('product_id')}\n👤 Name: {data.get('name', 'N/A')}\n💳 UTR:"
        f" {data.get('utr')}\n💰 Price: ₹{data.get('price')}"
    )
    keyboard = {
        'inline_keyboard': [[
            {
                'text': '✅ Approve & Send Link',
                'callback_data': f'approve_{order_id}',
            },
            {'text': '❌ Reject', 'callback_data': f'reject_{order_id}'},
        ]]
    }
    requests.post(
        f'https://api.telegram.org/bot{BOT_TOKEN}/sendMessage',
        json={
            'chat_id': ADMIN_CHAT_ID,
            'text': msg,
            'parse_mode': 'Markdown',
            'reply_markup': keyboard,
        },
    )

  return jsonify({'status': 'success', 'order_id': order_id})


@app.route('/api/telegram/webhook', methods=['POST'])
def telegram_webhook():
  update = request.json
  if 'callback_query' in update:
    cb = update['callback_query']
    data = cb['data']
    chat_id = cb['message']['chat']['id']
    message_id = cb['message']['message_id']

    if data.startswith('approve_'):
      order_id = int(data.split('_')[1])
      for o in db['orders']:
        if o['id'] == order_id:
          o['status'] = 'approved'
          requests.post(
              f'https://api.telegram.org/bot{BOT_TOKEN}/editMessageText',
              json={
                  'chat_id': chat_id,
                  'message_id': message_id,
                  'text': f'✅ *Order #{order_id} Approved Successfully!*',
                  'parse_mode': 'Markdown',
              },
          )
          break
    elif data.startswith('reject_'):
      order_id = int(data.split('_')[1])
      for o in db['orders']:
        if o['id'] == order_id:
          o['status'] = 'rejected'
          requests.post(
              f'https://api.telegram.org/bot{BOT_TOKEN}/editMessageText',
              json={
                  'chat_id': chat_id,
                  'message_id': message_id,
                  'text': f'❌ *Order #{order_id} Rejected.*',
                  'parse_mode': 'Markdown',
              },
          )
          break
  return jsonify({'status': 'ok'})


if __name__ == '__main__':
  app.run(host='0.0.0.0', port=int(os.environ.get('PORT', 5000)))
