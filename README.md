# Premium Group Hub + Baba Jadugar Panel

Professional Telegram Mini App sales system with full Admin Panel.

## Features

### Mini App (Premium Group Hub)
- Dark luxury premium theme
- Animated glowing borders
- Product cards with VIP/Premium tags
- Lock overlay on video/image → "GET FULL ACCESS"
- Price + Validity display
- Get Full Access button
- QR Code + Bill details
- **Pay Online** button (opens UPI app directly)
- UTR submission + auto status check
- After admin approval → Premium Group Link

### Admin Panel (Baba Jadugar Panel)
- Secure password login
- Dashboard: Today / Week / Total earnings, Pending UTRs, Views, Products count
- Products: Add / Edit / Delete
  - Title, Description, Price, Image URL, Group Link, Validity, Tags
- Orders: View all UTRs, Approve / Reject
- Settings: Mini App name, UPI ID, Bill description, Admin password
- Live sync → Panel changes reflect instantly on Mini App

## Default Login
- Password: `baba123`  
  (Change it from Settings after first login)

## How to Deploy

1. Upload this folder to GitHub
2. Deploy on Railway / Render / Heroku
3. Set environment variable if needed: `SECRET_KEY=any-random-string`
4. After deploy:
   - Mini App URL → use this as Telegram Mini App
   - Admin Panel → `yourdomain.com/admin`

## Local Run

```bash
pip install -r requirements.txt
python main.py
```

- Mini App: http://localhost:5000
- Admin: http://localhost:5000/admin

## Telegram Mini App Setup
1. Create bot with @BotFather
2. /newapp → select bot → set Mini App URL to your deployed link
3. Done
