from flask import Flask, request, jsonify, send_from_directory
import os

app = Flask(__name__, static_folder='static')

# डेटा स्टोरेज (एक सिंपल लिस्ट में - इसे तुम बाद में डेटाबेस से जोड़ सकते हो)
db = {
    "products": [],
    "orders": [],
    "config": {"upi_id": "yourname@upi", "payment_note": "Scan QR & Pay"}
}

@app.route('/')
def index(): return send_from_directory('static', 'index.html')

@app.route('/admin')
def admin(): return send_from_directory('static', 'admin.html')

@app.route('/api/admin/login', methods=['POST'])
def login():
    data = request.json
    if data.get('username') == 'admin' and data.get('password') == 'admin123':
        return jsonify({'status': 'success'})
    return jsonify({'status': 'error'}), 401

@app.route('/api/admin/dashboard')
def dashboard():
    return jsonify({
        "revenue": sum(float(o['price']) for o in db['orders'] if o['status'] == 'approved'),
        "total_buyers": len([o for o in db['orders'] if o['status'] == 'approved']),
        "orders": db['orders'],
        "products": db['products'],
        "upi_id": db['config']['upi_id'],
        "payment_note": db['config']['payment_note']
    })

@app.route('/api/admin/save-product', methods=['POST'])
def save_product():
    data = request.json
    if 'id' in data:
        for p in db['products']:
            if p['id'] == data['id']:
                p.update(data)
    else:
        data['id'] = len(db['products']) + 1
        db['products'].append(data)
    return jsonify({'status': 'success'})

@app.route('/api/admin/approve-order', methods=['POST'])
def approve():
    oid = request.json['order_id']
    for o in db['orders']:
        if o['id'] == oid: o['status'] = 'approved'
    return jsonify({'status': 'success'})

@app.route('/api/data')
def get_data():
    return jsonify(db)

@app.route('/api/order/submit', methods=['POST'])
def submit():
    data = request.json
    data['id'] = len(db['orders']) + 1
    data['status'] = 'pending'
    # प्रोडक्ट प्राइस ढूँढो
    prod = next((p for p in db['products'] if p['id'] == data['product_id']), {})
    data['price'] = prod.get('price', 0)
    data['title'] = prod.get('title', 'N/A')
    db['orders'].append(data)
    return jsonify({'status': 'success'})

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=int(os.environ.get('PORT', 5000)))
    
