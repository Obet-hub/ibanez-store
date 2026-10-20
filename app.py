import http.server
import socketserver
import json
import urllib.parse
import os
import sqlite3
from datetime import datetime

PORT = int(os.environ.get("PORT", 8000))
DB_FILE = "vault_store.db"

def init_db():
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    
    # Inventory Table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS inventory (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            stock INTEGER NOT NULL,
            price REAL NOT NULL,
            cost REAL NOT NULL,
            category TEXT DEFAULT 'General'
        )
    ''')
    
    # Transactions / Sales Table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS transactions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            items TEXT NOT NULL,
            total REAL NOT NULL,
            payment REAL NOT NULL,
            change REAL NOT NULL,
            customer TEXT,
            timestamp TEXT NOT NULL
        )
    ''')
    
    # Expenses Table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS expenses (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            description TEXT NOT NULL,
            amount REAL NOT NULL,
            category TEXT NOT NULL,
            timestamp TEXT NOT NULL
        )
    ''')
    
    # Users Table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            password TEXT NOT NULL,
            role TEXT NOT NULL
        )
    ''')
    
    # Insert default users if empty
    cursor.execute("SELECT COUNT(*) FROM users")
    if cursor.fetchone()[0] == 0:
        default_users = [
            ("Admin", "admin123", "admin"),
            ("Store Keeper", "store123", "storekeeper")
        ]
        cursor.executemany("INSERT INTO users (username, password, role) VALUES (?, ?, ?)", default_users)
        
    # Insert sample inventory if empty
    cursor.execute("SELECT COUNT(*) FROM inventory")
    if cursor.fetchone()[0] == 0:
        sample_items = [
            ("Premium Rice 50kg", 20, 2200.0, 1950.0, "Grains"),
            ("Regular Rice 25kg", 15, 1100.0, 980.0, "Grains"),
            ("Canned Sardines", 100, 25.0, 20.0, "Canned Goods"),
            ("Cooking Oil 1L", 50, 95.0, 80.0, "Essentials")
        ]
        cursor.executemany("INSERT INTO inventory (name, stock, price, cost, category) VALUES (?, ?, ?, ?, ?)", sample_items)
        
    conn.commit()
    conn.close()

init_db()

HTML_CONTENT = """<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Ibañez Vault Store POS & Ledger</title>
    <script src="https://cdn.tailwindcss.com"></script>
    <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
</head>
<body class="bg-slate-900 text-slate-100 font-sans antialiased min-h-screen flex flex-col">

    <!-- LOGIN SCREEN -->
    <div id="login-screen" class="fixed inset-0 bg-slate-950 flex items-center justify-center z-50 p-4">
        <div class="bg-slate-900 border border-slate-800 p-6 rounded-2xl shadow-2xl w-full max-w-sm">
            <h2 class="text-2xl font-bold text-center mb-6 text-indigo-400">Ibañez Vault Store</h2>
            <form id="login-form" onsubmit="handleLogin(event)" class="space-y-4">
                <div>
                    <label class="block text-xs font-semibold uppercase tracking-wider text-slate-400 mb-1">Username</label>
                    <input type="text" id="login-user" required class="w-full bg-slate-800 border border-slate-700 rounded-lg px-4 py-2.5 text-white focus:outline-none focus:border-indigo-500">
                </div>
                <div>
                    <label class="block text-xs font-semibold uppercase tracking-wider text-slate-400 mb-1">Password</label>
                    <input type="password" id="login-pass" placeholder="Enter password" required class="w-full bg-slate-800 border border-slate-700 rounded-lg px-4 py-2.5 text-white focus:outline-none focus:border-indigo-500">
                </div>
                <button type="submit" class="w-full bg-indigo-600 hover:bg-indigo-500 text-white font-semibold py-2.5 rounded-lg transition duration-200 shadow-lg">Login</button>
                <p id="login-error" class="text-red-400 text-sm text-center hidden">Invalid username or password.</p>
            </form>
        </div>
    </div>

    <!-- MAIN APP CONTAINER -->
    <div id="app-container" class="hidden flex flex-col flex-1">
        <!-- HEADER -->
        <header class="bg-slate-900 border-b border-slate-800 sticky top-0 z-40">
            <div class="max-w-7xl mx-auto px-4 py-3 flex justify-between items-center">
                <h1 class="text-lg font-bold text-indigo-400">Ibañez Vault POS</h1>
                <div class="flex items-center gap-3">
                    <span id="user-badge" class="text-xs px-2.5 py-1 bg-slate-800 rounded-full border border-slate-700 text-slate-300"></span>
                    <button onclick="logout()" class="text-xs bg-red-600/20 text-red-400 hover:bg-red-600/30 px-3 py-1.5 rounded-lg border border-red-500/30 transition">Logout</button>
                </div>
            </div>
            <!-- NAVIGATION TABS -->
            <div class="max-w-7xl mx-auto px-4 flex gap-2 overflow-x-auto pb-2 scrollbar-none">
                <button onclick="switchTab('pos')" id="tab-pos" class="tab-btn px-4 py-2 text-sm font-semibold rounded-lg bg-indigo-600 text-white transition">POS</button>
                <button onclick="switchTab('calc')" id="tab-calc" class="tab-btn px-4 py-2 text-sm font-semibold rounded-lg bg-slate-800 text-slate-400 hover:bg-slate-700 transition">Calculators</button>
                <button onclick="switchTab('inventory')" id="tab-inventory" class="tab-btn px-4 py-2 text-sm font-semibold rounded-lg bg-slate-800 text-slate-400 hover:bg-slate-700 transition">Inventory</button>
                <button onclick="switchTab('ledger')" id="tab-ledger" class="tab-btn px-4 py-2 text-sm font-semibold rounded-lg bg-slate-800 text-slate-400 hover:bg-slate-700 transition">Ledger & P&L</button>
                <button onclick="switchTab('users')" id="tab-users" class="tab-btn px-4 py-2 text-sm font-semibold rounded-lg bg-slate-800 text-slate-400 hover:bg-slate-700 transition">Users</button>
            </div>
        </header>

        <!-- CONTENT SECTIONS -->
        <main class="max-w-7xl mx-auto px-4 py-6 flex-1 w-full">
            
            <!-- POS TAB -->
            <section id="section-pos" class="space-y-6">
                <div class="grid grid-cols-1 lg:grid-cols-3 gap-6">
                    <div class="lg:col-span-2 space-y-4">
                        <input type="text" id="pos-search" placeholder="Search product..." oninput="filterPOSItems()" class="w-full bg-slate-800 border border-slate-700 rounded-lg px-4 py-2.5 text-white focus:outline-none focus:border-indigo-500">
                        <div id="pos-grid" class="grid grid-cols-2 sm:grid-cols-3 gap-3 max-h-[500px] overflow-y-auto pr-1"></div>
                    </div>
                    <div class="bg-slate-800/50 border border-slate-800 p-4 rounded-xl flex flex-col justify-between h-[500px]">
                        <div>
                            <h3 class="font-bold text-base mb-3 text-indigo-300">Current Sale</h3>
                            <div id="cart-list" class="space-y-2 overflow-y-auto max-h-[220px] pr-1 divide-y divide-slate-700/50"></div>
                        </div>
                        <div class="border-t border-slate-700 pt-4 space-y-3">
                            <div class="flex justify-between text-lg font-bold">
                                <span>Total:</span>
                                <span id="cart-total" class="text-indigo-400">₱0.00</span>
                            </div>
                            <input type="number" id="cash-given" placeholder="Cash Amount" oninput="calculateChange()" class="w-full bg-slate-800 border border-slate-700 rounded-lg px-3 py-2 text-white focus:outline-none focus:border-indigo-500">
                            <div class="flex justify-between text-sm text-slate-300">
                                <span>Change:</span>
                                <span id="change-due" class="font-semibold text-emerald-400">₱0.00</span>
                            </div>
                            <button onclick="checkout()" class="w-full bg-emerald-600 hover:bg-emerald-500 text-white font-semibold py-2.5 rounded-lg transition shadow-lg">Complete Sale</button>
                        </div>
                    </div>
                </div>
            </section>

            <!-- CALCULATORS TAB -->
            <section id="section-calc" class="hidden space-y-6">
                <div class="grid grid-cols-1 md:grid-cols-2 gap-6">
                    <!-- Rice Per Kilo Calculator -->
                    <div class="bg-slate-800/50 border border-slate-800 p-5 rounded-xl space-y-4">
                        <h3 class="font-bold text-lg text-indigo-300 border-b border-slate-700 pb-2">🍚 Rice Per-Kilo Margin Calculator</h3>
                        <div class="space-y-3">
                            <div>
                                <label class="text-xs text-slate-400">Sack Cost (₱)</label>
                                <input type="number" id="rice-cost" value="1950" oninput="calcRice()" class="w-full bg-slate-800 border border-slate-700 rounded-lg px-3 py-2 text-white">
                            </div>
                            <div>
                                <label class="text-xs text-slate-400">Sack Weight (kg)</label>
                                <input type="number" id="rice-weight" value="50" oninput="calcRice()" class="w-full bg-slate-800 border border-slate-700 rounded-lg px-3 py-2 text-white">
                            </div>
                            <div>
                                <label class="text-xs text-slate-400">Target Selling Price / kg (₱)</label>
                                <input type="number" id="rice-sell" value="48" oninput="calcRice()" class="w-full bg-slate-800 border border-slate-700 rounded-lg px-3 py-2 text-white">
                            </div>
                        </div>
                        <div class="bg-slate-900 p-4 rounded-lg space-y-2 border border-slate-800 text-sm">
                            <div class="flex justify-between"><span>Base Cost / kg:</span><span id="rice-cost-kg" class="font-bold text-slate-200">₱0.00</span></div>
                            <div class="flex justify-between"><span>Profit / kg:</span><span id="rice-profit-kg" class="font-bold text-emerald-400">₱0.00</span></div>
                            <div class="flex justify-between border-t border-slate-800 pt-2"><span>Total Sack Profit:</span><span id="rice-profit-sack" class="font-bold text-indigo-400">₱0.00</span></div>
                        </div>
                    </div>

                    <!-- Bulk Packaging Calculator -->
                    <div class="bg-slate-800/50 border border-slate-800 p-5 rounded-xl space-y-4">
                        <h3 class="font-bold text-lg text-indigo-300 border-b border-slate-700 pb-2">📦 Bulk Box & Reseller Pricing</h3>
                        <div class="space-y-3">
                            <div>
                                <label class="text-xs text-slate-400">Bulk Box Cost (₱)</label>
                                <input type="number" id="bulk-cost" value="1200" oninput="calcBulk()" class="w-full bg-slate-800 border border-slate-700 rounded-lg px-3 py-2 text-white">
                            </div>
                            <div>
                                <label class="text-xs text-slate-400">Units Per Box</label>
                                <input type="number" id="bulk-units" value="24" oninput="calcBulk()" class="w-full bg-slate-800 border border-slate-700 rounded-lg px-3 py-2 text-white">
                            </div>
                            <div>
                                <label class="text-xs text-slate-400">Desired Margin (%)</label>
                                <input type="number" id="bulk-margin" value="20" oninput="calcBulk()" class="w-full bg-slate-800 border border-slate-700 rounded-lg px-3 py-2 text-white">
                            </div>
                        </div>
                        <div class="bg-slate-900 p-4 rounded-lg space-y-2 border border-slate-800 text-sm">
                            <div class="flex justify-between"><span>Unit Cost:</span><span id="bulk-unit-cost" class="font-bold text-slate-200">₱0.00</span></div>
                            <div class="flex justify-between"><span>Suggested Retail Price:</span><span id="bulk-srp" class="font-bold text-emerald-400">₱0.00</span></div>
                            <div class="flex justify-between border-t border-slate-800 pt-2"><span>Total Box Profit:</span><span id="bulk-total-profit" class="font-bold text-indigo-400">₱0.00</span></div>
                        </div>
                    </div>
                </div>
            </section>

            <!-- INVENTORY TAB -->
            <section id="section-inventory" class="hidden space-y-6">
                <div id="add-item-card" class="bg-slate-800/50 border border-slate-800 p-4 rounded-xl">
                    <h3 class="font-bold text-base mb-3 text-indigo-300">Add New Inventory Item</h3>
                    <form onsubmit="addInventoryItem(event)" class="grid grid-cols-1 sm:grid-cols-5 gap-3">
                        <input type="text" id="item-name" placeholder="Item Name" required class="bg-slate-800 border border-slate-700 rounded-lg px-3 py-2 text-white">
                        <input type="number" id="item-stock" placeholder="Stock" required class="bg-slate-800 border border-slate-700 rounded-lg px-3 py-2 text-white">
                        <input type="number" step="0.01" id="item-price" placeholder="Selling Price" required class="bg-slate-800 border border-slate-700 rounded-lg px-3 py-2 text-white">
                        <input type="number" step="0.01" id="item-cost" placeholder="Unit Cost" required class="bg-slate-800 border border-slate-700 rounded-lg px-3 py-2 text-white">
                        <button type="submit" class="bg-indigo-600 hover:bg-indigo-500 font-semibold py-2 rounded-lg text-white">Add Item</button>
                    </form>
                </div>
                <div class="bg-slate-800/50 border border-slate-800 rounded-xl overflow-x-auto">
                    <table class="w-full text-left border-collapse">
                        <thead>
                            <tr class="border-b border-slate-700 text-xs uppercase text-slate-400 bg-slate-800/80">
                                <th class="p-3">Name</th>
                                <th class="p-3">Category</th>
                                <th class="p-3">Stock</th>
                                <th class="p-3">Price</th>
                                <th class="p-3">Cost</th>
                                <th class="p-3 text-right action-col">Actions</th>
                            </tr>
                        </thead>
                        <tbody id="inventory-table-body" class="divide-y divide-slate-800 text-sm"></tbody>
                    </table>
                </div>
            </section>

            <!-- LEDGER & P&L TAB -->
            <section id="section-ledger" class="hidden space-y-6">
                <div class="grid grid-cols-1 sm:grid-cols-4 gap-4">
                    <div class="bg-slate-800/50 border border-slate-800 p-4 rounded-xl">
                        <p class="text-xs text-slate-400 uppercase font-semibold">Total Revenue</p>
                        <h4 id="pnl-revenue" class="text-2xl font-bold text-emerald-400 mt-1">₱0.00</h4>
                    </div>
                    <div class="bg-slate-800/50 border border-slate-800 p-4 rounded-xl">
                        <p class="text-xs text-slate-400 uppercase font-semibold">Total Expenses</p>
                        <h4 id="pnl-expenses" class="text-2xl font-bold text-red-400 mt-1">₱0.00</h4>
                    </div>
                    <div class="bg-slate-800/50 border border-slate-800 p-4 rounded-xl">
                        <p class="text-xs text-slate-400 uppercase font-semibold">Net Profit</p>
                        <h4 id="pnl-net" class="text-2xl font-bold text-indigo-400 mt-1">₱0.00</h4>
                    </div>
                    <div class="bg-slate-800/50 border border-slate-800 p-4 rounded-xl flex items-center justify-center">
                        <button onclick="openExpenseModal()" class="w-full bg-rose-600 hover:bg-rose-500 font-semibold py-2.5 rounded-lg text-white">Record Expense</button>
                    </div>
                </div>
                <div class="bg-slate-800/50 border border-slate-800 p-4 rounded-xl">
                    <h3 class="font-bold text-base mb-3 text-indigo-300">Recent Transactions</h3>
                    <div class="overflow-x-auto">
                        <table class="w-full text-left border-collapse">
                            <thead>
                                <tr class="border-b border-slate-700 text-xs uppercase text-slate-400 bg-slate-800/80">
                                    <th class="p-3">Time</th>
                                    <th class="p-3">Items Sold</th>
                                    <th class="p-3">Total</th>
                                </tr>
                            </thead>
                            <tbody id="transactions-table-body" class="divide-y divide-slate-800 text-sm"></tbody>
                        </table>
                    </div>
                </div>
            </section>

            <!-- USERS TAB -->
            <section id="section-users" class="hidden space-y-6">
                <div class="bg-slate-800/50 border border-slate-800 p-4 rounded-xl">
                    <h3 class="font-bold text-base mb-3 text-indigo-300">Add New User</h3>
                    <form onsubmit="addUser(event)" class="grid grid-cols-1 sm:grid-cols-4 gap-3">
                        <input type="text" id="new-username" placeholder="Username" required class="bg-slate-800 border border-slate-700 rounded-lg px-3 py-2 text-white">
                        <input type="password" id="new-password" placeholder="Password" required class="bg-slate-800 border border-slate-700 rounded-lg px-3 py-2 text-white">
                        <select id="new-role" class="bg-slate-800 border border-slate-700 rounded-lg px-3 py-2 text-white">
                            <option value="storekeeper">Store Keeper</option>
                            <option value="admin">Admin</option>
                        </select>
                        <button type="submit" class="bg-indigo-600 hover:bg-indigo-500 font-semibold py-2 rounded-lg text-white">Create User</button>
                    </form>
                </div>
                <div class="bg-slate-800/50 border border-slate-800 rounded-xl overflow-x-auto">
                    <table class="w-full text-left border-collapse">
                        <thead>
                            <tr class="border-b border-slate-700 text-xs uppercase text-slate-400 bg-slate-800/80">
                                <th class="p-3">Username</th>
                                <th class="p-3">Role</th>
                                <th class="p-3 text-right">Actions</th>
                            </tr>
                        </thead>
                        <tbody id="users-table-body" class="divide-y divide-slate-800 text-sm"></tbody>
                    </table>
                </div>
            </section>

        </main>
    </div>

    <!-- EXPENSE MODAL -->
    <div id="expense-modal" class="fixed inset-0 bg-slate-950/80 hidden items-center justify-center z-50 p-4">
        <div class="bg-slate-900 border border-slate-800 p-6 rounded-2xl w-full max-w-sm space-y-4">
            <h3 class="text-lg font-bold text-indigo-400">Record Expense</h3>
            <form onsubmit="recordExpense(event)" class="space-y-3">
                <input type="text" id="exp-desc" placeholder="Description" required class="w-full bg-slate-800 border border-slate-700 rounded-lg px-3 py-2 text-white">
                <input type="number" step="0.01" id="exp-amount" placeholder="Amount (₱)" required class="w-full bg-slate-800 border border-slate-700 rounded-lg px-3 py-2 text-white">
                <input type="text" id="exp-cat" placeholder="Category" required class="w-full bg-slate-800 border border-slate-700 rounded-lg px-3 py-2 text-white">
                <div class="flex gap-2 pt-2">
                    <button type="button" onclick="closeExpenseModal()" class="flex-1 bg-slate-800 hover:bg-slate-700 py-2 rounded-lg text-slate-300 font-semibold">Cancel</button>
                    <button type="submit" class="flex-1 bg-rose-600 hover:bg-rose-500 py-2 rounded-lg text-white font-semibold">Save</button>
                </div>
            </form>
        </div>
    </div>

    <script>
        let currentUser = null;
        let inventory = [];
        let cart = [];
        let transactions = [];
        let expenses = [];
        let users = [];

        async function handleLogin(e) {
            e.preventDefault();
            const u = document.getElementById('login-user').value;
            const p = document.getElementById('login-pass').value;
            const res = await fetch('/api/login', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({username: u, password: p})
            });
            const data = await res.json();
            if(data.success) {
                currentUser = data.user;
                document.getElementById('login-screen').classList.add('hidden');
                document.getElementById('app-container').classList.remove('hidden');
                document.getElementById('user-badge').innerText = `${currentUser.username} (${currentUser.role})`;
                
                // Enforce Role restrictions
                if (currentUser.role !== 'admin') {
                    document.getElementById('tab-users').style.display = 'none';
                    document.getElementById('add-item-card').style.display = 'none';
                } else {
                    document.getElementById('tab-users').style.display = 'inline-block';
                    document.getElementById('add-item-card').style.display = 'block';
                }
                loadData();
                calcRice();
                calcBulk();
            } else {
                document.getElementById('login-error').classList.remove('hidden');
            }
        }

        function logout() {
            currentUser = null;
            document.getElementById('login-user').value = '';
            document.getElementById('login-pass').value = '';
            document.getElementById('login-screen').classList.remove('hidden');
            document.getElementById('app-container').classList.add('hidden');
        }

        function switchTab(tab) {
            ['pos', 'calc', 'inventory', 'ledger', 'users'].forEach(t => {
                document.getElementById(`section-${t}`).classList.add('hidden');
                document.getElementById(`tab-${t}`).classList.remove('bg-indigo-600', 'text-white');
                document.getElementById(`tab-${t}`).classList.add('bg-slate-800', 'text-slate-400');
            });
            document.getElementById(`section-${tab}`).classList.remove('hidden');
            document.getElementById(`tab-${tab}`).classList.add('bg-indigo-600', 'text-white');
            document.getElementById(`tab-${tab}`).classList.remove('bg-slate-800', 'text-slate-400');
            if(tab === 'ledger') loadLedgerData();
            if(tab === 'users' && currentUser.role === 'admin') loadUsersData();
        }

        async function loadData() {
            const res = await fetch('/api/data');
            const data = await res.json();
            inventory = data.inventory;
            transactions = data.transactions;
            expenses = data.expenses;
            renderPOS();
            renderInventory();
        }

        function renderPOS(items = inventory) {
            const grid = document.getElementById('pos-grid');
            grid.innerHTML = items.map(item => `
                <div onclick="addToCart(${item.id})" class="bg-slate-800/70 hover:bg-slate-700/80 border border-slate-700/50 p-3 rounded-xl cursor-pointer transition flex flex-col justify-between">
                    <div>
                        <h4 class="font-semibold text-sm truncate text-white">${item.name}</h4>
                        <p class="text-xs text-slate-400 mt-1">Stock: ${item.stock}</p>
                    </div>
                    <div class="mt-3 flex justify-between items-center">
                        <span class="text-indigo-400 font-bold text-sm">₱${item.price.toFixed(2)}</span>
                    </div>
                </div>
            `).join('');
        }

        function filterPOSItems() {
            const q = document.getElementById('pos-search').value.toLowerCase();
            renderPOS(inventory.filter(i => i.name.toLowerCase().includes(q)));
        }

        function addToCart(id) {
            const item = inventory.find(i => i.id === id);
            if(!item || item.stock <= 0) return alert("Out of stock!");
            const existing = cart.find(c => c.id === id);
            if(existing) {
                if(existing.qty < item.stock) existing.qty++;
            } else {
                cart.push({...item, qty: 1});
            }
            renderCart();
        }

        function renderCart() {
            const list = document.getElementById('cart-list');
            list.innerHTML = cart.map((c, index) => `
                <div class="py-2 flex justify-between items-center text-sm">
                    <div>
                        <p class="font-medium text-white">${c.name}</p>
                        <p class="text-xs text-slate-400">₱${c.price} x ${c.qty}</p>
                    </div>
                    <div class="flex items-center gap-2">
                        <span class="font-bold text-indigo-300">₱${(c.price * c.qty).toFixed(2)}</span>
                        <button onclick="removeFromCart(${index})" class="text-red-400 text-xs px-1.5 py-0.5 bg-red-500/10 rounded">✕</button>
                    </div>
                </div>
            `).join('');
            const total = cart.reduce((sum, c) => sum + (c.price * c.qty), 0);
            document.getElementById('cart-total').innerText = `₱${total.toFixed(2)}`;
            calculateChange();
        }

        function removeFromCart(index) {
            cart.splice(index, 1);
            renderCart();
        }

        function calculateChange() {
            const total = cart.reduce((sum, c) => sum + (c.price * c.qty), 0);
            const cash = parseFloat(document.getElementById('cash-given').value) || 0;
            const change = cash - total;
            document.getElementById('change-due').innerText = `₱${change >= 0 ? change.toFixed(2) : '0.00'}`;
        }

        async function checkout() {
            if(cart.length === 0) return alert("Cart is empty!");
            const total = cart.reduce((sum, c) => sum + (c.price * c.qty), 0);
            const cash = parseFloat(document.getElementById('cash-given').value) || 0;
            if(cash < total) return alert("Insufficient cash!");
            
            const res = await fetch('/api/checkout', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({cart, total, cash, change: cash - total})
            });
            const data = await res.json();
            if(data.success) {
                alert("Sale successful!");
                cart = [];
                document.getElementById('cash-given').value = '';
                renderCart();
                loadData();
            } else {
                alert("Checkout failed.");
            }
        }

        function calcRice() {
            const cost = parseFloat(document.getElementById('rice-cost').value) || 0;
            const weight = parseFloat(document.getElementById('rice-weight').value) || 1;
            const sell = parseFloat(document.getElementById('rice-sell').value) || 0;
            
            const costKg = cost / weight;
            const profitKg = sell - costKg;
            const totalProfit = profitKg * weight;

            document.getElementById('rice-cost-kg').innerText = `₱${costKg.toFixed(2)}`;
            document.getElementById('rice-profit-kg').innerText = `₱${profitKg.toFixed(2)}`;
            document.getElementById('rice-profit-sack').innerText = `₱${totalProfit.toFixed(2)}`;
        }

        function calcBulk() {
            const cost = parseFloat(document.getElementById('bulk-cost').value) || 0;
            const units = parseFloat(document.getElementById('bulk-units').value) || 1;
            const margin = parseFloat(document.getElementById('bulk-margin').value) || 0;

            const unitCost = cost / units;
            const srp = unitCost * (1 + (margin / 100));
            const totalProfit = (srp - unitCost) * units;

            document.getElementById('bulk-unit-cost').innerText = `₱${unitCost.toFixed(2)}`;
            document.getElementById('bulk-srp').innerText = `₱${srp.toFixed(2)}`;
            document.getElementById('bulk-total-profit').innerText = `₱${totalProfit.toFixed(2)}`;
        }

        function renderInventory() {
            const tbody = document.getElementById('inventory-table-body');
            tbody.innerHTML = inventory.map(item => `
                <tr class="border-b border-slate-800/60 hover:bg-slate-800/30">
                    <td class="p-3 font-medium text-white">${item.name}</td>
                    <td class="p-3 text-slate-400">${item.category}</td>
                    <td class="p-3 text-slate-300">${item.stock}</td>
                    <td class="p-3 text-slate-300">₱${item.price.toFixed(2)}</td>
                    <td class="p-3 text-slate-300">₱${item.cost.toFixed(2)}</td>
                    <td class="p-3 text-right action-col">
                        ${currentUser && currentUser.role === 'admin' ? `
                            <button onclick="deleteItem(${item.id})" class="bg-red-500/10 text-red-400 hover:bg-red-500/20 px-2 py-1 rounded text-xs">Delete</button>
                        ` : '<span class="text-xs text-slate-500">Restricted</span>'}
                    </td>
                </tr>
            `).join('');
            
            if(currentUser && currentUser.role !== 'admin') {
                document.querySelectorAll('.action-col').forEach(el => el.style.display = 'none');
            } else {
                document.querySelectorAll('.action-col').forEach(el => el.style.display = 'table-cell');
            }
        }

        async function addInventoryItem(e) {
            e.preventDefault();
            if(currentUser.role !== 'admin') return alert("Access denied.");
            const newItem = {
                name: document.getElementById('item-name').value,
                stock: parseInt(document.getElementById('item-stock').value),
                price: parseFloat(document.getElementById('item-price').value),
                cost: parseFloat(document.getElementById('item-cost').value),
                category: 'General'
            };
            const res = await fetch('/api/inventory', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify(newItem)
            });
            if((await res.json()).success) {
                document.getElementById('item-name').value = '';
                document.getElementById('item-stock').value = '';
                document.getElementById('item-price').value = '';
                document.getElementById('item-cost').value = '';
                loadData();
            }
        }

        async function deleteItem(id) {
            if(currentUser.role !== 'admin') return alert("Access denied.");
            if(!confirm("Delete this item?")) return;
            const res = await fetch(`/api/inventory?id=${id}`, {method: 'DELETE'});
            if((await res.json()).success) loadData();
        }

        function loadLedgerData() {
            const rev = transactions.reduce((sum, t) => sum + t.total, 0);
            const exp = expenses.reduce((sum, e) => sum + e.amount, 0);
            document.getElementById('pnl-revenue').innerText = `₱${rev.toFixed(2)}`;
            document.getElementById('pnl-expenses').innerText = `₱${exp.toFixed(2)}`;
            document.getElementById('pnl-net').innerText = `₱${(rev - exp).toFixed(2)}`;
            
            const tbody = document.getElementById('transactions-table-body');
            tbody.innerHTML = transactions.slice().reverse().map(t => `
                <tr class="border-b border-slate-800/60">
                    <td class="p-3 text-slate-400 text-xs">${t.timestamp}</td>
                    <td class="p-3 text-slate-300 text-xs">${t.items}</td>
                    <td class="p-3 text-emerald-400 font-semibold">₱${t.total.toFixed(2)}</td>
                </tr>
            `).join('');
        }

        function openExpenseModal() {
            document.getElementById('expense-modal').classList.remove('hidden');
            document.getElementById('expense-modal').classList.add('flex');
        }

        function closeExpenseModal() {
            document.getElementById('expense-modal').classList.add('hidden');
            document.getElementById('expense-modal').classList.remove('flex');
        }

        async function recordExpense(e) {
            e.preventDefault();
            const exp = {
                description: document.getElementById('exp-desc').value,
                amount: parseFloat(document.getElementById('exp-amount').value),
                category: document.getElementById('exp-cat').value
            };
            const res = await fetch('/api/expenses', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify(exp)
            });
            if((await res.json()).success) {
                closeExpenseModal();
                document.getElementById('exp-desc').value = '';
                document.getElementById('exp-amount').value = '';
                document.getElementById('exp-cat').value = '';
                loadData();
            }
        }

        async function loadUsersData() {
            if(currentUser.role !== 'admin') return;
            const res = await fetch('/api/users');
            users = await res.json();
            const tbody = document.getElementById('users-table-body');
            tbody.innerHTML = users.map(u => `
                <tr class="border-b border-slate-800/60">
                    <td class="p-3 font-medium text-white">${u.username}</td>
                    <td class="p-3 text-slate-400 uppercase text-xs">${u.role}</td>
                    <td class="p-3 text-right">
                        ${u.username !== 'Admin' ? `<button onclick="deleteUser(${u.id})" class="bg-red-500/10 text-red-400 hover:bg-red-500/20 px-2 py-1 rounded text-xs">Delete</button>` : '<span class="text-xs text-slate-500">Protected</span>'}
                    </td>
                </tr>
            `).join('');
        }

        async function addUser(e) {
            e.preventDefault();
            if(currentUser.role !== 'admin') return alert("Access denied.");
            const newUser = {
                username: document.getElementById('new-username').value,
                password: document.getElementById('new-password').value,
                role: document.getElementById('new-role').value
            };
            const res = await fetch('/api/users', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify(newUser)
            });
            const data = await res.json();
            if(data.success) {
                document.getElementById('new-username').value = '';
                document.getElementById('new-password').value = '';
                loadUsersData();
            } else {
                alert(data.error || "Failed to create user.");
            }
        }

        async function deleteUser(id) {
            if(currentUser.role !== 'admin') return alert("Access denied.");
            if(!confirm("Delete this user?")) return;
            const res = await fetch(`/api/users?id=${id}`, {method: 'DELETE'});
            if((await res.json()).success) loadUsersData();
        }
    </script>
</body>
</html>
"""

class VaultHandler(http.server.SimpleHTTPRequestHandler):
    def do_GET(self):
        parsed_path = urllib.parse.urlparse(self.path)
        path = parsed_path.path
        query = urllib.parse.parse_qs(parsed_path.query)

        if path == '/':
            self.send_response(200)
            self.send_header('Content-Type', 'text/html')
            self.end_headers()
            self.wfile.write(HTML_CONTENT.encode('utf-8'))
        elif path == '/api/data':
            conn = sqlite3.connect(DB_FILE)
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            
            cursor.execute("SELECT * FROM inventory")
            inventory = [dict(row) for row in cursor.fetchall()]
            
            cursor.execute("SELECT * FROM transactions")
            transactions = [dict(row) for row in cursor.fetchall()]
            
            cursor.execute("SELECT * FROM expenses")
            expenses = [dict(row) for row in cursor.fetchall()]
            
            conn.close()
            
            data = {
                "inventory": inventory,
                "transactions": transactions,
                "expenses": expenses
            }
            self.send_response(200)
            self.send_header('Content-Type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps(data).encode('utf-8'))
        elif path == '/api/users':
            conn = sqlite3.connect(DB_FILE)
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            cursor.execute("SELECT id, username, role FROM users")
            users = [dict(row) for row in cursor.fetchall()]
            conn.close()
            self.send_response(200)
            self.send_header('Content-Type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps(users).encode('utf-8'))
        else:
            self.send_response(404)
            self.end_headers()

    def do_POST(self):
        content_length = int(self.headers.get('Content-Length', 0))
        post_data = self.rfile.read(content_length)
        data = json.loads(post_data.decode('utf-8')) if post_data else {}
        path = self.path

        if path == '/api/login':
            username = data.get('username')
            password = data.get('password')
            conn = sqlite3.connect(DB_FILE)
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM users WHERE username = ? AND password = ?", (username, password))
            user = cursor.fetchone()
            conn.close()
            
            if user:
                response = {"success": True, "user": {"id": user["id"], "username": user["username"], "role": user["role"]}}
            else:
                response = {"success": False}
            
            self.send_response(200)
            self.send_header('Content-Type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps(response).encode('utf-8'))

        elif path == '/api/checkout':
            cart = data.get('cart', [])
            total = data.get('total', 0)
            payment = data.get('cash', 0)
            change = data.get('change', 0)
            items_desc = ", ".join([f"{c['name']} (x{c['qty']})" for c in cart])
            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            
            conn = sqlite3.connect(DB_FILE)
            cursor = conn.cursor()
            cursor.execute("INSERT INTO transactions (items, total, payment, change, timestamp) VALUES (?, ?, ?, ?, ?)",
                           (items_desc, total, payment, change, timestamp))
            
            for c in cart:
                cursor.execute("UPDATE inventory SET stock = stock - ? WHERE id = ?", (c['qty'], c['id']))
                
            conn.commit()
            conn.close()
            
            self.send_response(200)
            self.send_header('Content-Type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps({"success": True}).encode('utf-8'))

        elif path == '/api/inventory':
            conn = sqlite3.connect(DB_FILE)
            cursor = conn.cursor()
            cursor.execute("INSERT INTO inventory (name, stock, price, cost, category) VALUES (?, ?, ?, ?, ?)",
                           (data.get('name'), data.get('stock'), data.get('price'), data.get('cost'), data.get('category', 'General')))
            conn.commit()
            conn.close()
            self.send_response(200)
            self.send_header('Content-Type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps({"success": True}).encode('utf-8'))

        elif path == '/api/expenses':
            conn = sqlite3.connect(DB_FILE)
            cursor = conn.cursor()
            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            cursor.execute("INSERT INTO expenses (description, amount, category, timestamp) VALUES (?, ?, ?, ?)",
                           (data.get('description'), data.get('amount'), data.get('category'), timestamp))
            conn.commit()
            conn.close()
            self.send_response(200)
            self.send_header('Content-Type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps({"success": True}).encode('utf-8'))

        elif path == '/api/users':
            conn = sqlite3.connect(DB_FILE)
            cursor = conn.cursor()
            try:
                cursor.execute("INSERT INTO users (username, password, role) VALUES (?, ?, ?)",
                               (data.get('username'), data.get('password'), data.get('role')))
                conn.commit()
                success = True
                error = None
            except sqlite3.IntegrityError:
                success = False
                error = "Username already exists."
            conn.close()
            self.send_response(200)
            self.send_header('Content-Type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps({"success": success, "error": error}).encode('utf-8'))

    def do_DELETE(self):
        parsed_path = urllib.parse.urlparse(self.path)
        path = parsed_path.path
        query = urllib.parse.parse_qs(parsed_path.query)

        if path == '/api/inventory':
            item_id = query.get('id', [None])[0]
            conn = sqlite3.connect(DB_FILE)
            cursor = conn.cursor()
            cursor.execute("DELETE FROM inventory WHERE id = ?", (item_id,))
            conn.commit()
            conn.close()
            self.send_response(200)
            self.send_header('Content-Type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps({"success": True}).encode('utf-8'))
        elif path == '/api/users':
            user_id = query.get('id', [None])[0]
            conn = sqlite3.connect(DB_FILE)
            cursor = conn.cursor()
            cursor.execute("DELETE FROM users WHERE id = ?", (user_id,))
            conn.commit()
            conn.close()
            self.send_response(200)
            self.send_header('Content-Type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps({"success": True}).encode('utf-8'))

if __name__ == '__main__':
    with socketserver.TCPServer(("", PORT), VaultHandler) as httpd:
        print(f"Serving at port {PORT}")
        httpd.serve_forever()
