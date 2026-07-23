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
# Форма для клиентов (с отслеживанием статуса)
CLIENT_FORM = """
<!DOCTYPE html>
<html lang="ru">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Заявка в IT</title>
    <style>
        * { box-sizing: border-box; margin: 0; padding: 0; }
        body { font-family: 'Segoe UI', sans-serif; background: #e9ecef; display: flex; justify-content: center; align-items: center; min-height: 100vh; padding: 20px; }
        .container { background: white; padding: 30px; border-radius: 12px; box-shadow: 0 8px 30px rgba(0,0,0,0.12); width: 100%; max-width: 550px; }
        h2 { text-align: center; color: #333; margin-bottom: 20px; }
        .tabs { display: flex; gap: 10px; margin-bottom: 20px; border-bottom: 2px solid #dee2e6; }
        .tab { padding: 10px 20px; cursor: pointer; border: none; background: none; font-size: 14px; font-weight: 600; color: #6c757d; transition: all 0.3s; border-bottom: 3px solid transparent; }
        .tab:hover { color: #007bff; }
        .tab.active { color: #007bff; border-bottom-color: #007bff; }
        .tab-content { display: none; }
        .tab-content.active { display: block; }
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
        
        /* Стили для отслеживания */
        .track-container { padding: 10px 0; }
        .track-select { margin-bottom: 20px; }
        .track-info { background: #f8f9fa; padding: 20px; border-radius: 8px; min-height: 150px; }
        .track-info .no-tickets { text-align: center; color: #adb5bd; padding: 30px 0; }
        .track-info .ticket-item { border-bottom: 1px solid #dee2e6; padding: 15px 0; }
        .track-info .ticket-item:last-child { border-bottom: none; }
        .track-info .ticket-header { display: flex; justify-content: space-between; align-items: center; flex-wrap: wrap; gap: 10px; }
        .track-info .ticket-title { font-weight: 600; color: #212529; }
        .track-info .ticket-status { padding: 4px 12px; border-radius: 12px; font-size: 0.85em; font-weight: 600; }
        .status-delivered { background: #cce5ff; color: #004085; }
        .status-progress { background: #fff3cd; color: #856404; }
        .status-resolved { background: #d4edda; color: #155724; }
        .track-info .ticket-desc { color: #495057; margin-top: 8px; font-size: 0.95em; }
        .track-info .ticket-meta { color: #6c757d; font-size: 0.85em; margin-top: 5px; }
        .track-info .ticket-time { color: #adb5bd; font-size: 0.8em; margin-top: 5px; }
        .status-badge { display: inline-block; width: 10px; height: 10px; border-radius: 50%; margin-right: 6px; }
        .status-badge.delivered { background: #007bff; }
        .status-badge.progress { background: #ffc107; }
        .status-badge.resolved { background: #28a745; }
        .refresh-track { padding: 8px 16px; background: #28a745; color: white; border: none; border-radius: 6px; cursor: pointer; font-weight: 600; margin-top: 10px; }
        .refresh-track:hover { background: #218838; }
        .track-empty { text-align: center; padding: 40px 20px; color: #6c757d; }
        .track-empty .icon { font-size: 48px; margin-bottom: 10px; }
    </style>
</head>
<body>
    <div class="container">
        <h2>🔧 Заявка на ремонт</h2>
        
        <!-- Вкладки -->
        <div class="tabs">
            <button class="tab active" data-tab="create" onclick="switchTab('create')">📝 Создать заявку</button>
            <button class="tab" data-tab="track" onclick="switchTab('track')">📊 Отследить заявку</button>
        </div>
        
        <!-- Вкладка: Создание заявки -->
        <div class="tab-content active" id="tab-create">
            <form id="ticketForm">
                <input type="hidden" id="branch" value="№3">

                <label><span class="required">*</span> Фамилия и Имя</label>
                <input type="text" id="full_name" placeholder="Например: Иванов Иван" required>

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

                <div class="info-block">
                    <div><strong>📄 МФУ:</strong> <span class="mfu-info" id="mfu_display">Выберите окно</span></div>
                    <div><strong>💻 Имя компьютера:</strong> <span class="pc-info" id="pc_display">Выберите окно</span></div>
                </div>

                <label><span class="required">*</span> Описание поломки</label>
                <textarea id="description" placeholder="Опишите подробно, что случилось..." required></textarea>

                <div class="checkbox-group">
                    <input type="checkbox" id="urgent">
                    <label for="urgent">⚠️ Срочная заявка</label>
                </div>

                <button type="submit">📨 Отправить заявку</button>
                <div id="message"></div>
            </form>
        </div>
        
        <!-- Вкладка: Отслеживание -->
        <div class="tab-content" id="tab-track">
            <div class="track-container">
                <div class="track-select">
                    <label>🔍 Выберите окно для отслеживания</label>
                    <select id="track_window" onchange="trackTickets()">
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
                    <button class="refresh-track" onclick="trackTickets()">🔄 Обновить</button>
                </div>
                <div class="track-info" id="trackInfo">
                    <div class="no-tickets">📋 Выберите окно для просмотра заявок</div>
                </div>
            </div>
        </div>
    </div>

    <script>
        // Данные по окнам
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

        // Переключение вкладок
        function switchTab(tab) {
            document.querySelectorAll('.tab').forEach(t => t.classList.remove('active'));
            document.querySelectorAll('.tab-content').forEach(c => c.classList.remove('active'));
            
            document.querySelector(`.tab[data-tab="${tab}"]`).classList.add('active');
            document.getElementById(`tab-${tab}`).classList.add('active');
            
            if (tab === 'track') {
                trackTickets();
            }
        }

        // Обновление информации о МФУ
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

        // Отправка заявки
        document.getElementById('ticketForm').addEventListener('submit', async (e) => {
            e.preventDefault();
            const msgDiv = document.getElementById('message');
            msgDiv.className = '';
            msgDiv.style.display = 'none';

            const windowNum = document.getElementById('window_number').value;
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

        // Функция отслеживания заявок по окну
        async function trackTickets() {
            const windowNum = document.getElementById('track_window').value;
            const trackInfo = document.getElementById('trackInfo');
            
            if (!windowNum) {
                trackInfo.innerHTML = '<div class="no-tickets">📋 Выберите окно для просмотра заявок</div>';
                return;
            }

            try {
                const response = await fetch(`/get_tickets_by_window?window=${windowNum}`);
                const data = await response.json();
                
                if (data.tickets && data.tickets.length > 0) {
                    // Группируем заявки по статусам
                    const grouped = {
                        delivered: data.tickets.filter(t => t.status === 'delivered'),
                        'in-progress': data.tickets.filter(t => t.status === 'in-progress'),
                        resolved: data.tickets.filter(t => t.status === 'resolved')
                    };
                    
                    let html = `<h3 style="margin-top: 0; color: #212529;">🪟 Заявки для окна №${windowNum}</h3>`;
                    html += `<p style="color: #6c757d; font-size: 0.9em;">Всего заявок: ${data.tickets.length}</p>`;
                    
                    // Функция для отображения группы заявок
                    function renderTicketGroup(tickets, status, statusName, statusClass, icon) {
                        if (tickets.length === 0) return '';
                        return `
                            <div style="margin-top: 15px;">
                                <h4 style="color: #495057; margin-bottom: 10px;">${icon} ${statusName} (${tickets.length})</h4>
                                ${tickets.map(ticket => `
                                    <div class="ticket-item">
                                        <div class="ticket-header">
                                            <span class="ticket-title">👤 ${ticket.full_name}</span>
                                            <span class="ticket-status ${statusClass}">
                                                <span class="status-badge ${status === 'delivered' ? 'delivered' : status === 'in-progress' ? 'progress' : 'resolved'}"></span>
                                                ${statusName}
                                            </span>
                                        </div>
                                        <div class="ticket-desc">${ticket.description}</div>
                                        <div class="ticket-meta">
                                            📄 ${ticket.mfu || 'Не указано'} | 💻 ${ticket.pc_name || 'Не указано'}
                                            ${ticket.urgent ? ' | ⚠️ СРОЧНО' : ''}
                                        </div>
                                        <div class="ticket-time">🕒 ${ticket.time}</div>
                                    </div>
                                `).join('')}
                            </div>
                        `;
                    }
                    
                    html += renderTicketGroup(grouped.delivered, 'delivered', '📩 Доставлено', 'status-delivered', '📩');
                    html += renderTicketGroup(grouped['in-progress'], 'in-progress', '🔧 В работе', 'status-progress', '🔧');
                    html += renderTicketGroup(grouped.resolved, 'resolved', '✅ Решено', 'status-resolved', '✅');
                    
                    trackInfo.innerHTML = html;
                } else {
                    trackInfo.innerHTML = `
                        <div class="track-empty">
                            <div class="icon">📭</div>
                            <p>Для окна №${windowNum} нет заявок</p>
                            <p style="font-size: 0.9em; color: #adb5bd;">Создайте новую заявку на вкладке "Создать заявку"</p>
                        </div>
                    `;
                }
            } catch (error) {
                console.error('Error:', error);
                trackInfo.innerHTML = '<div class="no-tickets" style="color: #dc3545;">❌ Ошибка загрузки данных</div>';
            }
        }

        // Автоматическое обновление каждые 10 секунд, если вкладка активна
        let trackInterval = null;
        
        // Следим за переключением вкладок
        document.querySelectorAll('.tab').forEach(tab => {
            tab.addEventListener('click', function() {
                if (this.dataset.tab === 'track') {
                    if (trackInterval) clearInterval(trackInterval);
                    trackInterval = setInterval(trackTickets, 10000);
                } else {
                    if (trackInterval) {
                        clearInterval(trackInterval);
                        trackInterval = null;
                    }
                }
            });
        });

        // Начальная инициализация
        document.addEventListener('DOMContentLoaded', function() {
            // Запускаем автообновление если вкладка "Отследить" активна
            if (document.querySelector('.tab[data-tab="track"]').classList.contains('active')) {
                trackInterval = setInterval(trackTickets, 10000);
            }
        });
    </script>
</body>
</html>
"""

# Панель мониторинга с SSE и управлением статусами
ADMIN_PANEL = """
<!DOCTYPE html>
<html lang="ru">
<head>
    <meta charset="UTF-8">
    <title>Панель IT-специалиста</title>
    <style>
        body { font-family: 'Segoe UI', sans-serif; background: #f1f3f5; padding: 20px; }
        h1 { color: #212529; display: flex; align-items: center; gap: 10px; flex-wrap: wrap; }
        .controls { margin-bottom: 20px; display: flex; gap: 10px; flex-wrap: wrap; }
        button { padding: 10px 18px; border: none; border-radius: 6px; cursor: pointer; font-weight: 600; font-size: 14px; transition: all 0.2s; }
        button:hover { opacity: 0.85; transform: translateY(-1px); }
        button:active { transform: scale(0.95); }
        .btn-clear { background: #dc3545; color: white; }
        .btn-refresh { background: #007bff; color: white; }
        .ticket { background: white; padding: 16px; margin-bottom: 12px; border-radius: 8px; box-shadow: 0 2px 6px rgba(0,0,0,0.08); border-left: 5px solid #007bff; transition: all 0.3s; animation: slideIn 0.3s ease-out; }
        .ticket:hover { transform: translateX(3px); box-shadow: 0 4px 12px rgba(0,0,0,0.15); }
        .ticket.urgent { border-left-color: #dc3545; background: #fff5f5; animation: pulse 2s infinite, slideIn 0.3s ease-out; }
        .ticket.in-progress { border-left-color: #ffc107; background: #fffbf0; }
        .ticket.resolved { border-left-color: #28a745; background: #f0fff4; opacity: 0.85; }
        .ticket.resolved .desc { background: #e8f5e9; }
        @keyframes pulse { 0%,100% { box-shadow: 0 0 0 0 rgba(220,53,69,0.4); } 50% { box-shadow: 0 0 0 8px rgba(220,53,69,0); } }
        @keyframes slideIn {
            from { opacity: 0; transform: translateY(-20px); }
            to { opacity: 1; transform: translateY(0); }
        }
        .ticket-header { display: flex; justify-content: space-between; align-items: flex-start; margin-bottom: 6px; flex-wrap: wrap; gap: 8px; }
        .ticket-header strong { font-size: 1.1em; }
        .badge { padding: 3px 10px; border-radius: 12px; font-size: 0.8em; font-weight: bold; white-space: nowrap; }
        .badge-urgent { background: #dc3545; color: white; animation: blink 1.5s infinite; }
        .badge-normal { background: #e9ecef; color: #495057; }
        .badge-status { padding: 3px 10px; border-radius: 12px; font-size: 0.75em; font-weight: bold; }
        .badge-delivered { background: #007bff; color: white; }
        .badge-progress { background: #ffc107; color: #212529; }
        .badge-resolved { background: #28a745; color: white; }
        @keyframes blink { 0%,100% { opacity: 1; } 50% { opacity: 0.6; } }
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
        .ticket-actions { margin-top: 10px; display: flex; gap: 8px; flex-wrap: wrap; }
        .btn-status { padding: 5px 12px; border: none; border-radius: 4px; cursor: pointer; font-size: 0.8em; font-weight: 600; transition: all 0.2s; }
        .btn-status:hover { transform: scale(1.05); }
        .btn-status:active { transform: scale(0.95); }
        .btn-delivered { background: #007bff; color: white; }
        .btn-progress { background: #ffc107; color: #212529; }
        .btn-resolved { background: #28a745; color: white; }
        .btn-delete { background: #dc3545; color: white; }
        .status-filters { display: flex; gap: 8px; flex-wrap: wrap; margin-bottom: 15px; }
        .filter-btn { padding: 6px 14px; border: 2px solid #dee2e6; border-radius: 20px; background: white; cursor: pointer; font-size: 0.85em; transition: all 0.2s; }
        .filter-btn:hover { background: #f8f9fa; }
        .filter-btn.active { border-color: #007bff; background: #007bff; color: white; }
        .filter-btn.active-all { border-color: #6c757d; background: #6c757d; color: white; }
        .stats { display: flex; gap: 20px; flex-wrap: wrap; margin-bottom: 15px; }
        .stat-item { background: white; padding: 8px 16px; border-radius: 8px; box-shadow: 0 2px 4px rgba(0,0,0,0.05); }
        .stat-item span { font-weight: 600; }
        .stat-delivered { color: #007bff; }
        .stat-progress { color: #ffc107; }
        .stat-resolved { color: #28a745; }
    </style>
</head>
<body>
    <h1>🖥️ Поступившие заявки <span class="counter" id="counter">0</span></h1>
    
    <div class="stats">
        <div class="stat-item">📋 Всего: <span id="totalCount">0</span></div>
        <div class="stat-item stat-delivered">📩 Доставлено: <span id="deliveredCount">0</span></div>
        <div class="stat-item stat-progress">🔧 В работе: <span id="progressCount">0</span></div>
        <div class="stat-item stat-resolved">✅ Решено: <span id="resolvedCount">0</span></div>
    </div>
    
    <div class="status-filters">
        <button class="filter-btn active active-all" data-filter="all" onclick="setFilter('all')">📋 Все</button>
        <button class="filter-btn" data-filter="delivered" onclick="setFilter('delivered')">📩 Доставлено</button>
        <button class="filter-btn" data-filter="in-progress" onclick="setFilter('in-progress')">🔧 В работе</button>
        <button class="filter-btn" data-filter="resolved" onclick="setFilter('resolved')">✅ Решено</button>
    </div>
    
    <div class="controls">
        <button class="btn-refresh" onclick="location.reload()">🔄 Обновить</button>
        <button class="btn-clear" onclick="clearAllTickets()">🗑️ Очистить всё</button>
    </div>
    
    <div id="tickets-container">
        <div class="empty">⏳ Загрузка заявок...</div>
    </div>

    <script>
        let tickets = [];
        let currentFilter = 'all';
        let ticketIdCounter = 0;
        
        function renderTickets() {
            const container = document.getElementById('tickets-container');
            const counter = document.getElementById('counter');
            
            const total = tickets.length;
            const delivered = tickets.filter(t => t.status === 'delivered').length;
            const inProgress = tickets.filter(t => t.status === 'in-progress').length;
            const resolved = tickets.filter(t => t.status === 'resolved').length;
            
            document.getElementById('totalCount').textContent = total;
            document.getElementById('deliveredCount').textContent = delivered;
            document.getElementById('progressCount').textContent = inProgress;
            document.getElementById('resolvedCount').textContent = resolved;
            counter.textContent = total;
            
            let filteredTickets = tickets;
            if (currentFilter === 'delivered') {
                filteredTickets = tickets.filter(t => t.status === 'delivered');
            } else if (currentFilter === 'in-progress') {
                filteredTickets = tickets.filter(t => t.status === 'in-progress');
            } else if (currentFilter === 'resolved') {
                filteredTickets = tickets.filter(t => t.status === 'resolved');
            }
            
            if (filteredTickets.length === 0) {
                container.innerHTML = `<div class="empty">✨ ${currentFilter === 'all' ? 'Заявок пока нет. Ждём...' : 'Нет заявок с таким статусом'}</div>`;
                return;
            }
            
            const reversed = [...filteredTickets].reverse();
            
            container.innerHTML = reversed.map(ticket => {
                const statusBadge = {
                    'delivered': '<span class="badge-status badge-delivered">📩 Доставлено</span>',
                    'in-progress': '<span class="badge-status badge-progress">🔧 В работе</span>',
                    'resolved': '<span class="badge-status badge-resolved">✅ Решено</span>'
                }[ticket.status] || '<span class="badge-status badge-delivered">📩 Доставлено</span>';
                
                return `
                <div class="ticket ${ticket.urgent ? 'urgent' : ''} ${ticket.status === 'in-progress' ? 'in-progress' : ''} ${ticket.status === 'resolved' ? 'resolved' : ''}" id="ticket-${ticket.id}">
                    <div class="ticket-header">
                        <div>
                            <strong>👤 ${ticket.full_name}</strong>
                            ${ticket.urgent ? '<span class="badge badge-urgent">⚠️ СРОЧНО</span>' : '<span class="badge badge-normal">Обычная</span>'}
                            ${statusBadge}
                        </div>
                        <div style="font-size: 0.85em; color: #6c757d;">#${ticket.id}</div>
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
                    <div class="ticket-actions">
                        ${ticket.status !== 'in-progress' ? `<button class="btn-status btn-progress" onclick="updateStatus(${ticket.id}, 'in-progress')">🔧 В работу</button>` : ''}
                        ${ticket.status !== 'resolved' ? `<button class="btn-status btn-resolved" onclick="updateStatus(${ticket.id}, 'resolved')">✅ Решено</button>` : ''}
                        ${ticket.status !== 'delivered' ? `<button class="btn-status btn-delivered" onclick="updateStatus(${ticket.id}, 'delivered')">📩 Вернуть в доставлено</button>` : ''}
                        <button class="btn-status btn-delete" onclick="deleteTicket(${ticket.id})">🗑️ Удалить</button>
                    </div>
                </div>
            `}).join('');
        }
        
        async function updateStatus(ticketId, newStatus) {
            try {
                const response = await fetch('/update_status', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ id: ticketId, status: newStatus })
                });
                const result = await response.json();
                if (result.status === 'ok') {
                    const ticket = tickets.find(t => t.id === ticketId);
                    if (ticket) {
                        ticket.status = newStatus;
                        renderTickets();
                        showStatusNotification(ticket, newStatus);
                    }
                } else {
                    alert('Ошибка обновления статуса');
                }
            } catch (error) {
                console.error('Error:', error);
                alert('Ошибка обновления статуса');
            }
        }
        
        async function deleteTicket(ticketId) {
            if (!confirm('Удалить эту заявку?')) return;
            
            try {
                const response = await fetch('/delete_ticket', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ id: ticketId })
                });
                const result = await response.json();
                if (result.status === 'ok') {
                    tickets = tickets.filter(t => t.id !== ticketId);
                    renderTickets();
                } else {
                    alert('Ошибка удаления заявки');
                }
            } catch (error) {
                console.error('Error:', error);
                alert('Ошибка удаления заявки');
            }
        }
        
        function showStatusNotification(ticket, status) {
            const statusNames = {
                'delivered': '📩 Доставлено',
                'in-progress': '🔧 В работе',
                'resolved': '✅ Решено'
            };
            
            const toast = document.createElement('div');
            toast.className = 'toast';
            toast.textContent = `📌 Заявка #${ticket.id} (${ticket.full_name}) → ${statusNames[status]}`;
            document.body.appendChild(toast);
            
            setTimeout(() => {
                toast.style.opacity = '0';
                toast.style.transition = 'opacity 0.5s';
                setTimeout(() => toast.remove(), 500);
            }, 3000);
        }
        
        function setFilter(filter) {
            currentFilter = filter;
            document.querySelectorAll('.filter-btn').forEach(btn => {
                btn.classList.remove('active', 'active-all');
                if (btn.dataset.filter === filter) {
                    btn.classList.add('active');
                }
            });
            renderTickets();
        }
        
        function connectSSE() {
            const eventSource = new EventSource('/stream');
            
            eventSource.onmessage = function(event) {
                const data = JSON.parse(event.data);
                
                if (data.type === 'init') {
                    tickets = data.tickets;
                    if (tickets.length > 0) {
                        ticketIdCounter = Math.max(...tickets.map(t => t.id)) + 1;
                    }
                    renderTickets();
                } else if (data.type === 'new_ticket') {
                    tickets.push(data.ticket);
                    renderTickets();
                    showNotification(data.ticket);
                } else if (data.type === 'clear') {
                    tickets = [];
                    renderTickets();
                } else if (data.type === 'status_updated') {
                    const ticket = tickets.find(t => t.id === data.ticket.id);
                    if (ticket) {
                        ticket.status = data.ticket.status;
                        renderTickets();
                    }
                } else if (data.type === 'ticket_deleted') {
                    tickets = tickets.filter(t => t.id !== data.ticketId);
                    renderTickets();
                }
            };
            
            eventSource.onerror = function() {
                setTimeout(connectSSE, 3000);
            };
        }
        
        function showNotification(ticket) {
            const toast = document.createElement('div');
            toast.className = 'toast';
            toast.textContent = `🔔 Новая заявка #${ticket.id} от ${ticket.full_name} (Окно ${ticket.window_number})${ticket.urgent ? ' ⚠️ СРОЧНО!' : ''}`;
            document.body.appendChild(toast);
            
            setTimeout(() => {
                toast.style.opacity = '0';
                toast.style.transition = 'opacity 0.5s';
                setTimeout(() => toast.remove(), 500);
            }, 5000);
        }
        
        async function clearAllTickets() {
            if (confirm('Удалить ВСЕ заявки?')) {
                await fetch('/clear', { method: 'POST' });
            }
        }
        
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
        last_status = {t.get('id'): t.get('status') for t in tickets}
        
        while True:
            # Проверяем новые заявки
            if len(tickets) > last_id:
                new_ticket = tickets[-1]
                yield f"data: {json.dumps({'type': 'new_ticket', 'ticket': new_ticket})}\n\n"
                last_id = len(tickets)
            
            # Проверяем изменения статусов
            for ticket in tickets:
                ticket_id = ticket.get('id')
                current_status = ticket.get('status')
                if ticket_id in last_status and last_status[ticket_id] != current_status:
                    yield f"data: {json.dumps({'type': 'status_updated', 'ticket': ticket})}\n\n"
                    last_status[ticket_id] = current_status
            
            time.sleep(0.5)
    
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
    
    # Добавляем ID и статус
    ticket_id = len(tickets) + 1
    data['id'] = ticket_id
    data['status'] = 'delivered'  # Статус по умолчанию
    data['time'] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    # Добавляем данные по МФУ и ПК, если их нет
    if 'mfu' not in data:
        data['mfu'] = 'Не указано'
    if 'pc_name' not in data:
        data['pc_name'] = 'Не указано'
    
    tickets.append(data)
    
    print(f"🔥 НОВАЯ ЗАЯВКА #{ticket_id} | {data['full_name']} | Окно {data['window_number']}")
    print(f"   МФУ: {data['mfu']} | ПК: {data['pc_name']}")
    print(f"   Статус: {data['status']}")
    print(f"   Поломка: {data['description'][:60]}...")
    return jsonify({"status": "ok", "message": "Заявка принята!"}), 200

@app.route('/update_status', methods=['POST'])
def update_status():
    data = request.get_json()
    ticket_id = data.get('id')
    new_status = data.get('status')
    
    if not ticket_id or not new_status:
        return jsonify({"status": "error", "message": "Не указан ID или статус"}), 400
    
    # Ищем заявку по ID
    for ticket in tickets:
        if ticket.get('id') == ticket_id:
            old_status = ticket.get('status')
            ticket['status'] = new_status
            print(f"📌 Заявка #{ticket_id}: статус изменен с '{old_status}' на '{new_status}'")
            return jsonify({"status": "ok", "message": "Статус обновлен"}), 200
    
    return jsonify({"status": "error", "message": "Заявка не найдена"}), 404

@app.route('/delete_ticket', methods=['POST'])
def delete_ticket():
    data = request.get_json()
    ticket_id = data.get('id')
    
    if not ticket_id:
        return jsonify({"status": "error", "message": "Не указан ID"}), 400
    
    # Ищем и удаляем заявку
    for i, ticket in enumerate(tickets):
        if ticket.get('id') == ticket_id:
            deleted_ticket = tickets.pop(i)
            print(f"🗑️ Удалена заявка #{ticket_id} от {deleted_ticket.get('full_name')}")
            return jsonify({"status": "ok", "message": "Заявка удалена"}), 200
    
    return jsonify({"status": "error", "message": "Заявка не найдена"}), 404

@app.route('/get_tickets_by_window', methods=['GET'])
def get_tickets_by_window():
    window_num = request.args.get('window')
    
    if not window_num:
        return jsonify({"status": "error", "message": "Не указан номер окна"}), 400
    
    # Ищем заявки по окну (сортируем по времени - новые сверху)
    window_tickets = [t for t in tickets if str(t.get('window_number')) == str(window_num)]
    window_tickets.sort(key=lambda x: x.get('time', ''), reverse=True)
    
    return jsonify({"status": "ok", "tickets": window_tickets}), 200

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
    print("📌 Статусы: Доставлено → В работе → Решено")
    print("📊 Клиенты могут отслеживать статус своих заявок по окну")
    print("=" * 60)
    
    threading.Timer(1.5, lambda: webbrowser.open("http://127.0.0.1:8080/admin")).start()
    app.run(host='0.0.0.0', port=8080, debug=True, threaded=True)
