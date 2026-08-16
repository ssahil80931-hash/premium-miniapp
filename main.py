import os
import requests
from flask import Flask, jsonify, request, send_from_directory

# अगर static फोल्डर नहीं होगा, तो यह कोड अपने आप बना देगा ताकि 502 एरर न आए
if not os.path.exists('static'):
  os.makedirs('static')

# अगर index.html नहीं है, तो यह डिफॉल्ट फाइल बना देगा
index_path = os.path.join('static', 'index.html')
if not os.path.exists(index_path):
  with open(index_path, 'w', encoding='utf-8') as f:
    f.write("""<!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>VIP Video Vault</title>
        <style>
            body { background: #0b0f19; color: #fff; font-family: sans-serif; text-align: center; padding: 20px; }
            .vault-box { background: rgba(255, 255, 255, 0.05); border: 1px solid rgba(255, 255, 255, 0.1); padding: 20px; border-radius: 15px; margin-top: 20px; }
        </style>
    </head>
    <body>
        <div class="vault-box">
            <h2>🔥 VIP VIDEO VAULT</h2>
            <p>Store is up and running successfully!</p>
        </div>
    </body>
    </html>""")

app = Flask(__name__, static_folder='static')

BOT_TOKEN = os.environ.get('BOT_TOKEN', '')
ADMIN_CHAT_ID = os.environ.get('ADMIN_CHAT_ID', '')

db = {
    "products": [{
        "id": 1,
        "title": "VIP Video Vault - Full Access",
        "price": "99",
        "description": "Instant access to private vault.",
        "link": "https://t.me/+YourGroupInviteLink",
    }],
    "orders": [],
}


@app.route('/')
def index():
  return send_from_directory('static', 'index.html')


@app.route('/api/data')
def get_data():
  return jsonify(db)


@app.route('/api/order/submit', methods=['POST'])
def submit_order():
  data = request.json or {}
  order_id = len(db['orders']) + 1
  data['id'] = order_id
  data['status'] = 'pending'
  db['orders'].append(data)

  if BOT_TOKEN and ADMIN_CHAT_ID:
    try:
      msg = (
          f"🚨 *New VIP Order Received!*\n\n📦 Product ID:"
          f" {data.get('product_id')}\n👤 Name: {data.get('name', 'N/A')}\n💳"
          f" UTR: {data.get('utr')}\n💰 Price: ₹{data.get('price')}"
      )
      keyboard = {
          'inline_keyboard': [[
              {'text': '✅ Approve', 'callback_data': f'approve_{order_id}'},
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
    except Exception as e:
      print(f"Telegram Notification Error: {e}")

  return jsonify({'status': 'success', 'order_id': order_id})


if __name__ == '__main__':
  port = int(os.environ.get('PORT', 5000))
  app.run(host='0.0.0.0', port=port)
    
