from flask import Flask, render_template, jsonify
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime, timedelta
import random


app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///dashboard.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)


class Metric(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    ts = db.Column(db.DateTime, nullable=False)
    value = db.Column(db.Float, nullable=False)


    def to_dict(self):
        return {'id': self.id, 'ts': self.ts.isoformat(), 'value': self.value}


# DB 초기화 함수
def init_db():
    with app.app_context():
        db.create_all()
        if Metric.query.count() == 0:
            now = datetime.utcnow()
            for i in range(30):
                t = now - timedelta(days=29-i)
                # 랜덤 요소를 제거하고, i 값에 따라 일정한 비율로 증가
                m = Metric(ts=t, value=round(10 + i * 1.5, 2))
                db.session.add(m)
            db.session.commit()


@app.route('/')
def index():
    latest = Metric.query.order_by(Metric.ts.desc()).first()
    avg = db.session.query(db.func.avg(Metric.value)).scalar() or 0
    total = db.session.query(db.func.count(Metric.id)).scalar() or 0
    return render_template('dashboard.html', latest=latest, avg=round(avg,2), total=total)


@app.route('/api/data')
def api_data():
    rows = Metric.query.order_by(Metric.ts).all()
    data = [{'ts': r.ts.strftime('%Y-%m-%d'), 'value': r.value} for r in rows]
    return jsonify(data)


if __name__ == '__main__':
    init_db()
    app.run(debug=True)