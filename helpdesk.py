from flask import Flask, request, jsonify, render_template_string, Response
from datetime import datetime
import threading
import webbrowser
import socket
import json
import time

app = Flask(__name__)
tickets = []
clients = []  # Список подключенных клиентов SSE

# ================== HTML ШАБЛОНЫ ==================
# Форма для клиентов (с выбором окна и информацией о МФУ)
CLIENT_FORM = """
<!DOCTYPE html>
<html lang="ru">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Заявка в IT</title>
    <style>
        * { box-sizing: border-box; margin: 0; padding: 0; }
        body { font-family: 'Segoe UI', sans-serif; background: #e9ecef; display: flex; justify-content: center; align-items: center; min-height: 100vh; }
        .container { background: white; padding: 30px; border-radius: 12px; box-shadow: 0 8px 30px rgba(0,0,0,0.12); width: 100%; max-width: 500px; }
        h2 { text-align: center; color: #333; margin-bottom: 20px; }
        label { display: block; margin-top: 14px; font-weight: 600; color: #495057; font-size: 0.9em; }
        label .required { color: #dc3545; }
        input, select, textarea { width: 100%; padding: 10px 12px; margin-top: 4px; border: 1px solid #ced4da; border-radius: 6px; font-size: 14px; transition: border-color 0.2s; font-family: inherit; }
        input:focus, select:focus, textarea:focus { outline: none; border-color: #4dabf7; box-shadow: 0 0 0 3px rgba(77,171,247,0.15); }
        textarea { resize: vertical; min-height: 100px; }
        .checkbox-group { display: flex; align-items: center; margin-top: 16px; }
        .checkbox-group input { width: auto; margin-right: 10px; accent-color: #dc3545; transform: scale(1.2); }
        .checkbox-group label { margin-top: 0; color: #dc3545; cursor: pointer; }
        button { width: 100%; padding: 12px; margin-top: 22px; background: #007bff; color: white; border: none; border-radius: 6px; font-size: 16px; font-weight: 600; cursor: pointer; transition: background 0.2s; }
        button:hover { background: #0056b3; }
        button:active { transform: scale(0.98); }
        #message { margin-top: 15px; padding: 12px; border-radius: 6px; text-align: center; display: none; font-weight: 500; }
        .success { background: #d4edda; color: #155724; display: block !important; }
        .error { background: #f8d7da; color: #721c24; display: block !important; }
        .info-block { background: #f8f9fa; padding: 15px; border-radius: 6px; margin-top: 10px; border-left: 4px solid #007bff; }
        .info-block strong { color: #495057; }
        .info-block .mfu-info { color: #28a745; font-weight: 600; }
        .info-block .pc-info { color: #17a2b8; font-weight: 600; }
        select[multiple] { height: auto; min-height: 80px; }
    </style>
</head>
<body>
    <div class="container">
        <h2>🔧 Заявка на ремонт</h2>
        <form id="ticketForm">
            <!-- Филиал (фиксированный) -->
            <input type="hidden" id="branch" value="№3">

            <!-- 1. Фамилия и Имя -->
            <label><span class="required">*</span> Фамилия и Имя</label>
            <input type="text" id="full_name" placeholder="Например: Иванов Иван" required>

            <!-- 2. Номер окна -->
            <label><span class="required">*</span> Номер окна</label>
            <select id="window_number" required>
                <option value="">-- Выберите окно --</option>
                <option value="1">Окно №1</option>
                <option value="2">Окно №2</option>
                <option value="3">Окно №3</option>
                <option value="4">Окно №4</option>
                <option value="5">Окно №5</option>
                <option value="6">Окно №6</option>
                <option value="7">Окно №7</option>
                <option value="8">Окно №8</option>
                <option value="9">Окно №9</option>
                <option value="10">Окно №10</option>
                <option value="11">Окно №11</option>
                <option value="12">Окно №12</option>
                <option value="13">Окно №13</option>
                <option value="14">Окно №14</option>
                <option value="15">Окно №15</option>
                <option value="16">Окно №16</option>
                <option value="17">Окно №17</option>
                <option value="18">Окно №18</option>
                <option value="19">Окно №19</option>
                <option value="20">Окно №20</option>
            </select>

            <!-- 3. Информация о МФУ и компьютере -->
            <div class="info-block">
                <div><strong>📄 МФУ:</strong> <span class="mfu-info" id="mfu_display">Выберите окно</span></div>
                <div><strong>💻 Имя компьютера:</strong> <span class="pc-info" id="pc_display">Выберите окно</span></div>
            </div>

            <!-- 4. Поломка -->
            <label><span class="required">*</span> Описание поломки</label>
            <textarea id="description" placeholder="Опишите подробно, что случилось..." required></textarea>

            <!-- Срочность -->
            <div class="checkbox-group">
                <input type="checkbox" id="urgent">
                <label for="urgent">⚠️ Срочная заявка</label>
            </div>

            <button type="submit">📨 Отправить заявку</button>
            <div id="message"></div>
        </form>
    </div>

    <script>
        // Данные по окнам (МФУ и имя компьютера)
        const windowData = {
            1: { mfu: "Kyocera M2040dn", pc: "PC-01" },
            2: { mfu: "HP LaserJet M404", pc: "PC-02" },
            3: { mfu: "Xerox WorkCentre 6515", pc: "PC-03" },
            4: { mfu: "Canon i-SENSYS MF743Cdw", pc: "PC-04" },
            5: { mfu: "Brother MFC-L5750DW", pc: "PC-05" },
            6: { mfu: "Kyocera M2040dn", pc: "PC-06" },
            7: { mfu: "HP LaserJet M404", pc: "PC-07" },
            8: { mfu: "Xerox WorkCentre 6515", pc: "PC-08" },
            9: { mfu: "Canon i-SENSYS MF743Cdw", pc: "PC-09" },
            10: { mfu: "Brother MFC-L5750DW", pc: "PC-10" },
            11: { mfu: "Kyocera M2040dn", pc: "PC-11" },
            12: { mfu: "HP LaserJet M404", pc: "PC-12" },
            13: { mfu: "Xerox WorkCentre 6515", pc: "PC-13" },
            14: { mfu: "Canon i-SENSYS MF743Cdw", pc: "PC-14" },
            15: { mfu: "Brother MFC-L5750DW", pc: "PC-15" },
            16: { mfu: "Kyocera M2040dn", pc: "PC-16" },
            17: { mfu: "HP LaserJet M404", pc: "PC-17" },
            18: { mfu: "Xerox WorkCentre 6515", pc: "PC-18" },
            19: { mfu: "Canon i-SENSYS MF743Cdw", pc: "PC-19" },
            20: { mfu: "Brother MFC-L5750DW", pc: "PC-20" }
        };

        // Обновление информации при выборе окна
        document.getElementById('window_number').addEventListener('change', function() {
            const windowNum = this.value;
            const mfuDisplay = document.getElementById('mfu_display');
            const pcDisplay = document.getElementById('pc_display');
            
            if (windowNum && windowData[windowNum]) {
                mfuDisplay.textContent = windowData[windowNum].mfu;
                pcDisplay.textContent = windowData[windowNum].pc;
                mfuDisplay.style.color = '#28a745';
                pcDisplay.style.color = '#17a2b8';
            } else {
                mfuDisplay.textContent = 'Выберите окно';
                pcDisplay.textContent = 'Выберите окно';
                mfuDisplay.style.color = '#dc3545';
                pcDisplay.style.color = '#dc3545';
            }
        });

        document.getElementById('ticketForm').addEventListener('submit', async (e) => {
            e.preventDefault();
            const msgDiv = document.getElementById('message');
            msgDiv.className = '';
            msgDiv.style.display = 'none';

            const windowNum = document.getElementById('window_number').value;
            
            // Получаем данные по окну
            const windowInfo = windowData[windowNum] || { mfu: 'Неизвестно', pc: 'Неизвестно' };

            const data = {
                branch: '№3',
                full_name: document.getElementById('full_name').value.trim(),
                window_number: windowNum,
                mfu: windowInfo.mfu,
                pc_name: windowInfo.pc,
                description: document.getElementById('description').value.trim(),
                urgent: document.getElementById('urgent').checked
            };

            // Проверка обязательных полей
            if (!data.full_name || !data.window_number || !data.description) {
                msgDiv.className = 'error';
                msgDiv.textContent = '❌ Заполните все обязательные поля!';
                msgDiv.style.display = 'block';
                return;
            }

            try {
                const res = await fetch('/submit_ticket', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify(data)
                });
                const result = await res.json();
                if (res.ok) {
                    msgDiv.className = 'success';
                    msgDiv.textContent = '✅ Заявка успешно отправлена!';
                    msgDiv.style.display = 'block';
                    document.getElementById('ticketForm').reset();
                    document.getElementById('mfu_display').textContent = 'Выберите окно';
                    document.getElementById('pc_display').textContent = 'Выберите окно';
                } else {
                    throw new Error(result.message || 'Ошибка сервера');
                }
            } catch (err) {
                msgDiv.className = 'error';
                msgDiv.textContent = '❌ ' + err.message;
                msgDiv.style.display = 'block';
            }
        });
    </script>
</body>
</html>
"""

# Панель мониторинга с SSE (обновлена для отображения информации об окне)
ADMIN_PANEL = """
<!DOCTYPE html>
<html lang="ru">
<head>
    <meta charset="UTF-8">
    <title>Панель IT-специалиста</title>
    <style>
        body { font-family: 'Segoe UI', sans-serif; background: #f1f3f5; padding: 20px; }
        h1 { color: #212529; display: flex; align-items: center; gap: 10px; }
        .controls { margin-bottom: 20px; display: flex; gap: 10px; flex-wrap: wrap; }
        button { padding: 10px 18px; border: none; border-radius: 6px; cursor: pointer; font-weight: 600; font-size: 14px; transition: opacity 0.2s; }
        button:hover { opacity: 0.85; }
        .btn-clear { background: #dc3545; color: white; }
        .btn-refresh { background: #007bff; color: white; }
        .btn-sound { background: #6c757d; color: white; }
        .ticket { background: white; padding: 16px; margin-bottom: 12px; border-radius: 8px; box-shadow: 0 2px 6px rgba(0,0,0,0.08); border-left: 5px solid #007bff; transition: transform 0.1s; animation: slideIn 0.3s ease-out; }
        .ticket:hover { transform: translateX(3px); }
        .ticket.urgent { border-left-color: #dc3545; background: #fff5f5; animation: pulse 2s infinite, slideIn 0.3s ease-out; }
        @keyframes pulse { 0%,100% { box-shadow: 0 0 0 0 rgba(220,53,69,0.4); } 50% { box-shadow: 0 0 0 8px rgba(220,53,69,0); } }
        @keyframes slideIn {
            from { opacity: 0; transform: translateY(-20px); }
            to { opacity: 1; transform: translateY(0); }
        }
        .ticket-header { display: flex; justify-content: space-between; align-items: flex-start; margin-bottom: 6px; flex-wrap: wrap; gap: 8px; }
        .ticket-header strong { font-size: 1.1em; }
        .badge { padding: 3px 10px; border-radius: 12px; font-size: 0.8em; font-weight: bold; white-space: nowrap; }
        .badge-urgent { background: #dc3545; color: white; }
        .badge-normal { background: #e9ecef; color: #495057; }
        .meta { color: #868e96; font-size: 0.85em; margin-top: 5px; display: flex; gap: 15px; flex-wrap: wrap; }
        .meta-info { display: flex; gap: 10px; flex-wrap: wrap; margin-top: 5px; }
        .meta-info span { background: #f8f9fa; padding: 2px 10px; border-radius: 4px; font-size: 0.85em; }
        .mfu-badge { color: #28a745; font-weight: 600; }
        .pc-badge { color: #17a2b8; font-weight: 600; }
        .desc { color: #343a40; margin-top: 8px; white-space: pre-wrap; background: #f8f9fa; padding: 10px; border-radius: 6px; font-size: 0.95em; }
        .time { color: #adb5bd; font-size: 0.8em; margin-top: 8px; }
        .empty { text-align: center; color: #adb5bd; padding: 40px; font-size: 1.1em; }
        .counter { background: #007bff; color: white; padding: 3px 12px; border-radius: 15px; font-size: 0.85em; }
        .toast { position: fixed; top: 20px; right: 20px; background: #28a745; color: white; padding: 15px 25px; border-radius: 8px; box-shadow: 0 4px 12px rgba(0,0,0,0.2); animation: slideInRight 0.5s ease-out; z-index: 1000; }
        @keyframes slideInRight {
            from { opacity: 0; transform: translateX(100px); }
            to { opacity: 1; transform: translateX(0); }
        }
    </style>
</head>
<body>
    <h1>🖥️ Поступившие заявки <span class="counter" id="counter">0</span></h1>
    <div class="controls">
        <button class="btn-refresh" onclick="location.reload()">🔄 Обновить</button>
        <button class="btn-clear" onclick="clearTickets()">🗑️ Очистить всё</button>
    </div>
    <div id="tickets-container">
        <div class="empty">⏳ Загрузка заявок...</div>
    </div>

    <script>
        let tickets = [];
        
        // Функция для отображения заявок
        function renderTickets() {
            const container = document.getElementById('tickets-container');
            const counter = document.getElementById('counter');
            
            counter.textContent = tickets.length;
            
            if (tickets.length === 0) {
                container.innerHTML = '<div class="empty">✨ Заявок пока нет. Ждём...</div>';
                return;
            }
            
            // Показываем в обратном порядке (сначала новые)
            const reversed = [...tickets].reverse();
            
            container.innerHTML = reversed.map(ticket => `
                <div class="ticket ${ticket.urgent ? 'urgent' : ''}">
                    <div class="ticket-header">
                        <strong>👤 ${ticket.full_name}</strong>
                        ${ticket.urgent ? '<span class="badge badge-urgent">⚠️ СРОЧНО</span>' : '<span class="badge badge-normal">Обычная</span>'}
                    </div>
                    <div class="meta">
                        <span>🏢 ${ticket.branch}</span>
                        <span>🪟 Окно №${ticket.window_number}</span>
                    </div>
                    <div class="meta-info">
                        <span class="mfu-badge">📄 МФУ: ${ticket.mfu || 'Не указано'}</span>
                        <span class="pc-badge">💻 ПК: ${ticket.pc_name || 'Не указано'}</span>
                    </div>
                    <div class="desc">${ticket.description}</div>
                    <div class="time">🕒 ${ticket.time}</div>
                </div>
            `).join('');
        }
        
        // Подключение к SSE
        function connectSSE() {
            const eventSource = new EventSource('/stream');
            
            eventSource.onmessage = function(event) {
                const data = JSON.parse(event.data);
                
                if (data.type === 'init') {
                    // Начальная загрузка всех заявок
                    tickets = data.tickets;
                    renderTickets();
                } else if (data.type === 'new_ticket') {
                    // Новая заявка
                    tickets.push(data.ticket);
                    renderTickets();
                    
                    // Показываем уведомление
                    showNotification(data.ticket);
                    
                    // Звуковой сигнал (если поддерживается)
                    playSound();
                } else if (data.type === 'clear') {
                    // Очистка
                    tickets = [];
                    renderTickets();
                }
            };
            
            eventSource.onerror = function() {
                // Переподключение через 3 секунды
                setTimeout(connectSSE, 3000);
            };
        }
        
        // Уведомление
        function showNotification(ticket) {
            const toast = document.createElement('div');
            toast.className = 'toast';
            toast.textContent = `🔔 Новая заявка от ${ticket.full_name} (Окно ${ticket.window_number})${ticket.urgent ? ' ⚠️ СРОЧНО!' : ''}`;
            document.body.appendChild(toast);
            
            setTimeout(() => {
                toast.style.opacity = '0';
                toast.style.transition = 'opacity 0.5s';
                setTimeout(() => toast.remove(), 500);
            }, 5000);
        }
        
        // Звук
        function playSound() {
            try {
                const audioCtx = new (window.AudioContext || window.webkitAudioContext)();
                const oscillator = audioCtx.createOscillator();
                const gainNode = audioCtx.createGain();
                oscillator.connect(gainNode);
                gainNode.connect(audioCtx.destination);
                oscillator.frequency.value = 800;
                oscillator.type = 'sine';
                gainNode.gain.setValueAtTime(0.3, audioCtx.currentTime);
                oscillator.start();
                oscillator.stop(audioCtx.currentTime + 0.2);
            } catch(e) {
                // Если звук не поддерживается, игнорируем
            }
        }
        
        // Очистка заявок
        async function clearTickets() {
            if (confirm('Удалить ВСЕ заявки?')) {
                await fetch('/clear', { method: 'POST' });
                // SSE автоматически обновит список
            }
        }
        
        // Запускаем SSE
        connectSSE();
    </script>
</body>
</html>
"""

# ================== SSE (Server-Sent Events) ==================
@app.route('/stream')
def stream():
    def event_stream():
        # Отправляем текущие заявки при подключении
        yield f"data: {json.dumps({'type': 'init', 'tickets': tickets})}\n\n"
        
        # Ждем новые события
        last_id = len(tickets)
        while True:
            # Проверяем, есть ли новые заявки
            if len(tickets) > last_id:
                new_ticket = tickets[-1]
                yield f"data: {json.dumps({'type': 'new_ticket', 'ticket': new_ticket})}\n\n"
                last_id = len(tickets)
            time.sleep(0.5)  # Проверяем каждые 0.5 секунды
    
    return Response(event_stream(), mimetype="text/event-stream")

# ================== МАРШРУТЫ ==================
@app.route('/')
def client_form():
    return render_template_string(CLIENT_FORM)

@app.route('/admin')
def admin_panel():
    return render_template_string(ADMIN_PANEL)

@app.route('/submit_ticket', methods=['POST'])
def submit_ticket():
    data = request.get_json()
    
    # Проверка обязательных полей
    required = ['branch', 'full_name', 'window_number', 'description']
    for field in required:
        if not data or not data.get(field):
            return jsonify({"status": "error", "message": f"Поле '{field}' обязательно!"}), 400
    
    # Добавляем время
    data['time'] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    # Добавляем данные по МФУ и ПК, если их нет
    if 'mfu' not in data:
        data['mfu'] = 'Не указано'
    if 'pc_name' not in data:
        data['pc_name'] = 'Не указано'
    
    tickets.append(data)
    
    print(f"🔥 НОВАЯ ЗАЯВКА | {data['full_name']} | Окно {data['window_number']} | {data['branch']}")
    print(f"   МФУ: {data['mfu']} | ПК: {data['pc_name']}")
    print(f"   Поломка: {data['description'][:60]}...")
    return jsonify({"status": "ok", "message": "Заявка принята!"}), 200

@app.route('/clear', methods=['POST'])
def clear():
    count = len(tickets)
    tickets.clear()
    print(f"🗑️ Очищено {count} заявок")
    return jsonify({"status": "ok"}), 200

if __name__ == '__main__':
    local_ip = "172.17.6.52"
    
    print("=" * 60)
    print("🖥️  СЕРВЕР ЗАЯВОК ЗАПУЩЕН")
    print("=" * 60)
    print(f"📋 Панель мониторинга (для вас): http://127.0.0.1:8080/admin")
    print(f"📝 Форма для клиентов:          http://{local_ip}:8080/")
    print(f"🌐 Разошлите клиентам ссылку:   http://{local_ip}:8080/")
    print("=" * 60)
    print("✨ Заявки теперь отображаются МГНОВЕННО!")
    print("=" * 60)
    
    threading.Timer(1.5, lambda: webbrowser.open("http://127.0.0.1:8080/admin")).start()
    app.run(host='0.0.0.0', port=8080, debug=True, threaded=True)
