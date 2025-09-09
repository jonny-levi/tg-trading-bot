

def generate_recommendation(percent_change, price, avg_price):
    if price >= avg_price * 2:
        return "⚡ תנועה חדה – מתאים ל־Scalping בלבד"
    elif percent_change >= 8:
        return "⚠️ עלייה חדה – פוטנציאל גבוה אך יתכן תיקון"
    elif percent_change >= 3:
        return "✅ מומנטום חיובי – לשקול כניסה"
    else:
        return "🔍 ניטרלי – אין איתות כרגע"
