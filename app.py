from flask import Flask, jsonify, render_template
import db
import mqtt_client

app = Flask(__name__)

# 初始化数据库（创建表）
db.init_db()

# 启动 MQTT 订阅客户端
# 客户端会在后台运行，收到消息后自动写入数据库
mqtt_client_inst = mqtt_client.start_mqtt()

@app.route("/")
def index():
    """渲染主页"""
    return render_template("index.html")

@app.route("/api/latest")
def get_latest():
    """API: 获取所有设备的最新状态"""
    data = db.get_latest_status()
    return jsonify(data)

@app.route("/api/history")
def get_history():
    """API: 获取最近 50 条历史记录"""
    data = db.get_history(limit=50)
    return jsonify(data)

if __name__ == "__main__":
    # 注意：在 Debug 模式下 Flask 可能会启动两次，MQTT 也会连两次
    # 如果是本地开发测试，可以设置 use_reloader=False
    app.run(host="0.0.0.0", port=5000, debug=True, use_reloader=False)
