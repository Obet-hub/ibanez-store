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
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS inventory (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            category TEXT NOT NULL,
            cost_price REAL NOT NULL,
            selling_price REAL NOT NULL,
            stock INTEGER NOT NULL,
            unit TEXT NOT NULL
        )
    ''')
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS sales (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            date TEXT NOT NULL,
            items TEXT NOT NULL,
            total REAL NOT NULL,
            payment_method TEXT NOT NULL,
            cashier TEXT NOT NULL
        )
    ''')
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS expenses (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            date TEXT NOT NULL,
            category TEXT NOT NULL,
            amount REAL NOT NULL,
            notes TEXT
        )
    ''')
    
    # Insert default data if empty
    cursor.execute("SELECT COUNT(*) FROM inventory")
    if cursor.fetchone()[0] == 0:
        sample_items = [
            ("Premium Sinaging Rice (50kg)", "Rice", 2000.0, 2300.0, 15, "sack"),
            ("Regular Rice (per kilo)", "Rice", 45.0, 52.0, 200, "kg"),
            ("Sardines Tomato Sauce", "Canned Goods", 18.0, 22.0, 100, "pcs"),
            ("Instant Noodles Beef", "Groceries", 10.0, 13.0, 150, "pcs"),
            ("Cooking Oil 1L", "Groceries", 85.0, 100.0, 40, "bottle")
        ]
        cursor.executemany("INSERT INTO inventory (name, category, cost_price, selling_price, stock, unit) VALUES (?, ?, ?, ?, ?, ?)", sample_items)
    
    conn.commit()
    conn.close()

init_db()

HTML_TEMPLATE = """<!DOCTYPE html>
<html lang="en" class="dark">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Ibañez Vault Store App</title>
    <script src="https://cdn.tailwindcss.com"></script>
    <script>
        tailwind.config = {
            darkMode: 'class',
            theme: {
                extend: {
                    colors: {
                        obsidian: {
                            900: '#0b0f19',
                            800: '#111827',
                            700: '#1f2937',
                            600: '#374151'
                        }
                    }
                }
            }
        }
    </script>
    <style>
        .obsidian-card {
            background: linear-gradient(135deg, #1f2937 0%, #111827 100%);
            box-shadow: 0 10px 25px -5px rgba(0, 0, 0, 0.5), 0 8px 10px -6px rgba(0, 0, 0, 0.5);
            border: 1px solid rgba(255, 255, 255, 0.08);
        }
    </style>
</head>
<body class="bg-obsidian-900 text-gray-100 min-h-screen font-sans antialiased">
    <!-- Navbar -->
    <nav class="bg-obsidian-800 border-b border-gray-800 sticky top-0 z-50">
        <div class="max-w-7xl mx-auto px-4 py-3 flex justify-between items-center">
            <div class="flex items-center space-x-3">
                <div class="bg-blue-600 p-2 rounded-xl text-white font-black text-xl tracking-wider shadow-lg">IV</div>
                <div>
                    <h1 class="font-bold text-lg tracking-wide text-white">Ibañez Vault Store</h1>
                    <p class="text-xs text-gray-400">Secure POS & Inventory Management</p>
                </div>
            </div>
            
            <!-- Role Switcher & Status -->
            <div class="flex items-center space-x-4">
                <div class="flex items-center bg-obsidian-900 px-3 py-1.5 rounded-lg border border-gray-700">
                    <span class="text-xs text-gray-400 mr-2">Role:</span>
                    <select id="userRole" onchange="switchRole(this.value)" class="bg-transparent text-blue-400 font-semibold text-sm focus:outline-none cursor-pointer">
                        <option value="Admin" class="bg-obsidian-900 text-white">Admin (Full Access)</option>
                        <option value="Store Keeper" class="bg-obsidian-900 text-white">Store Keeper (Restricted)</option>
                    </select>
                </div>
            </div>
        </div>
        
        <!-- Navigation Tabs -->
        <div class="max-w-7xl mx-auto px-4 flex space-x-1 overflow-x-auto border-t border-gray-800 py-2">
            <button onclick="switchTab('pos')" id="tab-pos" class="tab-btn px-4 py-2 rounded-lg text-sm font-medium transition bg-blue-600 text-white shadow">🛒 POS & Sales</button>
            <button onclick="switchTab('calculators')" id="tab-calculators" class="tab-btn px-4 py-2 rounded-lg text-sm font-medium transition text-gray-400 hover:text-white">⚖️ Reseller Calcs</button>
            <button onclick="switchTab('inventory')" id="tab-inventory" class="tab-btn px-4 py-2 rounded-lg text-sm font-medium transition text-gray-400 hover:text-white">📦 Inventory</button>
            <button onclick="switchTab('expenses')" id="tab-expenses" class="tab-btn px-4 py-2 rounded-lg text-sm font-medium transition text-gray-400 hover:text-white admin-only">💸 Expenses</button>
            <button onclick="switchTab('reports')" id="tab-reports" class="tab-btn px-4 py-2 rounded-lg text-sm font-medium transition text-gray-400 hover:text-white admin-only">📊 P&L Reports</button>
        </div>
    </nav>

    <!-- Main Container -->
    <main class="max-w-7xl mx-auto px-4 py-6">
        
        <!-- POS TAB -->
        <section id="content-pos" class="tab-content grid grid-cols-1 lg:grid-cols-3 gap-6">
            <div class="lg:col-span-2 space-y-4">
                <div class="flex justify-between items-center">
                    <h2 class="text-xl font-bold text-white">Point of Sale</h2>
                    <input type="text" id="posSearch" placeholder="Search products..." onkeyup="filterPOSItems()" class="bg-obsidian-800 border border-gray-700 px-4 py-2 rounded-xl text-sm focus:outline-none focus:border-blue-500 w-64">
                </div>
                <div id="posGrid" class="grid grid-cols-2 md:grid-cols-3 gap-4 max-h-[600px] overflow-y-auto pr-2">
                    <!-- Loaded dynamically -->
                </div>
            </div>
            
            <!-- Cart Sidebar -->
            <div class="obsidian-card p-5 rounded-2xl flex flex-col justify-between h-[650px]">
                <div>
                    <h3 class="text-lg font-bold text-white mb-4 flex justify-between items-center">
                        <span>Current Order</span>
                        <button onclick="clearCart()" class="text-xs text-red-400 hover:underline">Clear All</button>
                    </h3>
                    <div id="cartItems" class="space-y-3 overflow-y-auto max-h-[350px] pr-1 mb-4">
                        <p class="text-gray-500 text-sm text-center py-10">Cart is empty</p>
                    </div>
                </div>
                
                <div class="border-t border-gray-800 pt-4 space-y-3">
                    <div class="flex justify-between text-sm text-gray-400">
                        <span>Items Count:</span>
                        <span id="cartCount">0</span>
                    </div>
                    <div class="flex justify-between text-lg font-bold text-white">
                        <span>Total Amount:</span>
                        <span id="cartTotal" class="text-blue-400">₱0.00</span>
                    </div>
                    <div>
                        <label class="block text-xs text-gray-400 mb-1">Payment Method</label>
                        <select id="paymentMethod" class="w-full bg-obsidian-800 border border-gray-700 rounded-xl px-3 py-2 text-sm text-white focus:outline-none">
                            <option value="Cash">Cash</option>
                            <option value="GCash">GCash / QR</option>
                            <option value="Credit">Store Credit / Utang</option>
                        </select>
                    </div>
                    <button onclick="checkout()" class="w-full bg-blue-600 hover:bg-blue-500 text-white font-bold py-3 rounded-xl transition shadow-lg">Complete Transaction</button>
                </div>
            </div>
        </section>

        <!-- CALCULATORS TAB -->
        <section id="content-calculators" class="tab-content hidden grid-cols-1 md:grid-cols-2 gap-6">
            <!-- Rice Reseller Calculator -->
            <div class="obsidian-card p-6 rounded-2xl space-y-4">
                <h2 class="text-xl font-bold text-white flex items-center">🌾 Rice Reseller Calculator</h2>
                <p class="text-xs text-gray-400">Calculate profit margins for wholesale rice sacks broken down into retail kilos.</p>
                
                <div class="space-y-3">
                    <div>
                        <label class="block text-xs text-gray-400 mb-1">Sack Cost Price (₱)</label>
                        <input type="number" id="riceSackCost" value="2000" oninput="calculateRice()" class="w-full bg-obsidian-800 border border-gray-700 rounded-xl px-3 py-2 text-sm text-white">
                    </div>
                    <div>
                        <label class="block text-xs text-gray-400 mb-1">Sack Weight (kg)</label>
                        <input type="number" id="riceSackWeight" value="50" oninput="calculateRice()" class="w-full bg-obsidian-800 border border-gray-700 rounded-xl px-3 py-2 text-sm text-white">
                    </div>
                    <div>
                        <label class="block text-xs text-gray-400 mb-1">Desired Retail Price per Kilo (₱)</label>
                        <input type="number" id="riceRetailPerKilo" value="52" oninput="calculateRice()" class="w-full bg-obsidian-800 border border-gray-700 rounded-xl px-3 py-2 text-sm text-white">
                    </div>
                </div>

                <div class="bg-obsidian-900 p-4 rounded-xl border border-gray-800 space-y-2 mt-4">
                    <div class="flex justify-between text-sm">
                        <span class="text-gray-400">Cost per Kilo:</span>
                        <span id="resCostPerKilo" class="font-semibold text-white">₱0.00</span>
                    </div>
                    <div class="flex justify-between text-sm">
                        <span class="text-gray-400">Total Potential Revenue:</span>
                        <span id="resTotalRev" class="font-semibold text-white">₱0.00</span>
                    </div>
                    <div class="flex justify-between text-sm font-bold border-t border-gray-800 pt-2">
                        <span class="text-blue-400">Estimated Profit per Sack:</span>
                        <span id="resTotalProfit" class="text-blue-400">₱0.00</span>
                    </div>
                </div>
            </div>

            <!-- Bulk Box Calculator -->
            <div class="obsidian-card p-6 rounded-2xl space-y-4">
                <h2 class="text-xl font-bold text-white flex items-center">📦 Bulk Box Pricing Calculator</h2>
                <p class="text-xs text-gray-400">Calculate retail unit price from wholesale box cost with desired markup percentage.</p>
                
                <div class="space-y-3">
                    <div>
                        <label class="block text-xs text-gray-400 mb-1">Whole Box Cost Price (₱)</label>
                        <input type="number" id="boxCost" value="850" oninput="calculateBox()" class="w-full bg-obsidian-800 border border-gray-700 rounded-xl px-3 py-2 text-sm text-white">
                    </div>
                    <div>
                        <label class="block text-xs text-gray-400 mb-1">Items / Units per Box</label>
                        <input type="number" id="boxUnits" value="24" oninput="calculateBox()" class="w-full bg-obsidian-800 border border-gray-700 rounded-xl px-3 py-2 text-sm text-white">
                    </div>
                    <div>
                        <label class="block text-xs text-gray-400 mb-1">Markup Percentage (%)</label>
                        <input type="number" id="boxMarkup" value="20" oninput="calculateBox()" class="w-full bg-obsidian-800 border border-gray-700 rounded-xl px-3 py-2 text-sm text-white">
                    </div>
                </div>

                <div class="bg-obsidian-900 p-4 rounded-xl border border-gray-800 space-y-2 mt-4">
                    <div class="flex justify-between text-sm">
                        <span class="text-gray-400">Cost per Individual Unit:</span>
                        <span id="boxCostPerUnit" class="font-semibold text-white">₱0.00</span>
                    </div>
                    <div class="flex justify-between text-sm font-bold border-t border-gray-800 pt-2">
                        <span class="text-blue-400">Recommended Selling Price / Unit:</span>
                        <span id="boxSellingPerUnit" class="text-blue-400 text-lg">₱0.00</span>
                    </div>
                </div>
            </div>
        </section>

        <!-- INVENTORY TAB -->
        <section id="content-inventory" class="tab-content hidden space-y-4">
            <div class="flex justify-between items-center flex-wrap gap-4">
                <h2 class="text-xl font-bold text-white">Inventory Management</h2>
                <div class="flex space-x-3">
                    <input type="text" id="invSearch" placeholder="Search inventory..." onkeyup="filterInventory()" class="bg-obsidian-800 border border-gray-700 px-4 py-2 rounded-xl text-sm focus:outline-none">
                    <button onclick="openAddModal()" class="admin-only bg-blue-600 hover:bg-blue-500 text-white px-4 py-2 rounded-xl text-sm font-semibold shadow transition">+ Add Product</button>
                </div>
            </div>

            <div class="obsidian-card rounded-2xl overflow-hidden border border-gray-800">
                <div class="overflow-x-auto">
                    <table class="w-full text-left border-collapse">
                        <thead>
                            <tr class="bg-obsidian-800 text-gray-400 text-xs uppercase border-b border-gray-700">
                                <th class="p-4">Product Name</th>
                                <th class="p-4">Category</th>
                                <th class="p-4">Cost Price</th>
                                <th class="p-4">Selling Price</th>
                                <th class="p-4">Stock</th>
                                <th class="p-4 text-right admin-only">Actions</th>
                            </tr>
                        </thead>
                        <tbody id="inventoryTable" class="divide-y divide-gray-800 text-sm">
                            <!-- Loaded dynamically -->
                        </tbody>
                    </table>
                </div>
            </div>
        </section>

        <!-- EXPENSES TAB -->
        <section id="content-expenses" class="tab-content hidden space-y-4">
            <div class="flex justify-between items-center">
                <h2 class="text-xl font-bold text-white">Store Expenses Tracker</h2>
                <button onclick="openExpenseModal()" class="bg-blue-600 hover:bg-blue-500 text-white px-4 py-2 rounded-xl text-sm font-semibold shadow">+ Log Expense</button>
            </div>
            
            <div class="obsidian-card rounded-2xl overflow-hidden border border-gray-800">
                <table class="w-full text-left border-collapse">
                    <thead>
                        <tr class="bg-obsidian-800 text-gray-400 text-xs uppercase border-b border-gray-700">
                            <th class="p-4">Date</th>
                            <th class="p-4">Category</th>
                            <th class="p-4">Amount</th>
                            <th class="p-4">Notes</th>
                            <th class="p-4 text-right">Action</th>
                        </tr>
                    </thead>
                    <tbody id="expensesTable" class="divide-y divide-gray-800 text-sm">
                        <!-- Loaded dynamically -->
                    </tbody>
                </table>
            </div>
        </section>

        <!-- REPORTS TAB -->
        <section id="content-reports" class="tab-content hidden space-y-6">
            <h2 class="text-xl font-bold text-white">Profit & Loss Financial Reports</h2>
            
            <div class="grid grid-cols-1 md:grid-cols-3 gap-6">
                <div class="obsidian-card p-5 rounded-2xl border border-gray-800">
                    <p class="text-xs text-gray-400">Total Gross Revenue</p>
                    <h3 id="repRevenue" class="text-2xl font-black text-white mt-1">₱0.00</h3>
                </div>
                <div class="obsidian-card p-5 rounded-2xl border border-gray-800">
                    <p class="text-xs text-gray-400">Total Recorded Expenses</p>
                    <h3 id="repExpenses" class="text-2xl font-black text-red-400 mt-1">₱0.00</h3>
                </div>
                <div class="obsidian-card p-5 rounded-2xl border border-gray-800">
                    <p class="text-xs text-gray-400">Net Profit</p>
                    <h3 id="repNetProfit" class="text-2xl font-black text-blue-400 mt-1">₱0.00</h3>
                </div>
            </div>

            <div class="obsidian-card p-6 rounded-2xl space-y-4">
                <h3 class="text-lg font-bold text-white">Sales Transaction History</h3>
                <div class="overflow-x-auto">
                    <table class="w-full text-left border-collapse">
                        <thead>
                            <tr class="bg-obsidian-800 text-gray-400 text-xs uppercase border-b border-gray-700">
                                <th class="p-3">ID</th>
                                <th class="p-3">Date</th>
                                <th class="p-3">Items Sold</th>
                                <th class="p-3">Method</th>
                                <th class="p-3">Cashier</th>
                                <th class="p-3 text-right">Total</th>
                            </tr>
                        </thead>
                        <tbody id="salesReportTable" class="divide-y divide-gray-800 text-sm">
                            <!-- Loaded dynamically -->
                        </tbody>
                    </table>
                </div>
            </div>
        </section>
    </main>

    <!-- MODALS -->
    <!-- Product Modal -->
    <div id="productModal" class="fixed inset-0 bg-black/70 hidden flex items-center justify-center z-50 p-4">
        <div class="obsidian-card max-w-md w-full p-6 rounded-2xl space-y-4 border border-gray-700">
            <h3 id="productModalTitle" class="text-lg font-bold text-white">Add New Product</h3>
            <input type="hidden" id="prodId">
            <div class="space-y-3">
                <div>
                    <label class="block text-xs text-gray-400 mb-1">Product Name</label>
                    <input type="text" id="prodName" class="w-full bg-obsidian-800 border border-gray-700 rounded-xl px-3 py-2 text-sm text-white">
                </div>
                <div class="grid grid-cols-2 gap-3">
                    <div>
                        <label class="block text-xs text-gray-400 mb-1">Category</label>
                        <input type="text" id="prodCategory" class="w-full bg-obsidian-800 border border-gray-700 rounded-xl px-3 py-2 text-sm text-white">
                    </div>
                    <div>
                        <label class="block text-xs text-gray-400 mb-1">Unit (pcs, sack, kg)</label>
                        <input type="text" id="prodUnit" class="w-full bg-obsidian-800 border border-gray-700 rounded-xl px-3 py-2 text-sm text-white">
                    </div>
                </div>
                <div class="grid grid-cols-2 gap-3">
                    <div>
                        <label class="block text-xs text-gray-400 mb-1">Cost Price (₱)</label>
                        <input type="number" id="prodCost" class="w-full bg-obsidian-800 border border-gray-700 rounded-xl px-3 py-2 text-sm text-white">
                    </div>
                    <div>
                        <label class="block text-xs text-gray-400 mb-1">Selling Price (₱)</label>
                        <input type="number" id="prodPrice" class="w-full bg-obsidian-800 border border-gray-700 rounded-xl px-3 py-2 text-sm text-white">
                    </div>
                </div>
                <div>
                    <label class="block text-xs text-gray-400 mb-1">Initial Stock</label>
                    <input type="number" id="prodStock" class="w-full bg-obsidian-800 border border-gray-700 rounded-xl px-3 py-2 text-sm text-white">
                </div>
            </div>
            <div class="flex justify-end space-x-3 pt-2">
                <button onclick="closeProductModal()" class="px-4 py-2 bg-gray-700 text-gray-300 rounded-xl text-sm font-semibold">Cancel</button>
                <button onclick="saveProduct()" class="px-4 py-2 bg-blue-600 text-white rounded-xl text-sm font-semibold">Save Product</button>
            </div>
        </div>
    </div>

    <!-- Expense Modal -->
    <div id="expenseModal" class="fixed inset-0 bg-black/70 hidden flex items-center justify-center z-50 p-4">
        <div class="obsidian-card max-w-md w-full p-6 rounded-2xl space-y-4 border border-gray-700">
            <h3 class="text-lg font-bold text-white">Log New Expense</h3>
            <div class="space-y-3">
                <div>
                    <label class="block text-xs text-gray-400 mb-1">Category (e.g. Electric, Rent)</label>
                    <input type="text" id="expCategory" class="w-full bg-obsidian-800 border border-gray-700 rounded-xl px-3 py-2 text-sm text-white">
                </div>
                <div>
                    <label class="block text-xs text-gray-400 mb-1">Amount (₱)</label>
                    <input type="number" id="expAmount" class="w-full bg-obsidian-800 border border-gray-700 rounded-xl px-3 py-2 text-sm text-white">
                </div>
                <div>
                    <label class="block text-xs text-gray-400 mb-1">Notes / Description</label>
                    <input type="text" id="expNotes" class="w-full bg-obsidian-800 border border-gray-700 rounded-xl px-3 py-2 text-sm text-white">
                </div>
            </div>
            <div class="flex justify-end space-x-3 pt-2">
                <button onclick="closeExpenseModal()" class="px-4 py-2 bg-gray-700 text-gray-300 rounded-xl text-sm font-semibold">Cancel</button>
                <button onclick="saveExpense()" class="px-4 py-2 bg-blue-600 text-white rounded-xl text-sm font-semibold">Log Expense</button>
            </div>
        </div>
    </div>

    <!-- Receipt Modal -->
    <div id="receiptModal" class="fixed inset-0 bg-black/80 hidden flex items-center justify-center z-50 p-4">
        <div class="bg-white text-gray-900 max-w-sm w-full p-6 rounded-2xl space-y-4 shadow-2xl">
            <div class="text-center border-b pb-3">
                <h2 class="font-black text-xl tracking-wider">IBAÑEZ VAULT STORE</h2>
                <p class="text-xs text-gray-500">Official Sales Receipt</p>
                <p id="receiptDate" class="text-xs text-gray-500 mt-1"></p>
            </div>
            <div id="receiptBody" class="space-y-2 text-sm">
                <!-- Items list -->
            </div>
            <div class="border-t pt-3 space-y-1">
                <div class="flex justify-between font-bold text-base">
                    <span>Total Paid:</span>
                    <span id="receiptTotal">₱0.00</span>
                </div>
                <div class="flex justify-between text-xs text-gray-500">
                    <span id="receiptMethod">Cash</span>
                    <span id="receiptCashier">Admin</span>
                </div>
            </div>
            <div class="flex space-x-3 pt-2">
                <button onclick="window.print()" class="w-full bg-gray-900 text-white py-2 rounded-xl text-sm font-semibold">Print Receipt</button>
                <button onclick="closeReceiptModal()" class="w-full bg-gray-200 text-gray-800 py-2 rounded-xl text-sm font-semibold">Close</button>
            </div>
        </div>
    </div>

    <script>
        let inventory = [];
        let cart = [];
        let currentRole = 'Admin';

        function switchRole(role) {
            currentRole = role;
            const adminElements = document.querySelectorAll('.admin-only');
            adminElements.forEach(el => {
                if (role === 'Store Keeper') {
                    el.classList.add('hidden');
                } else {
                    el.classList.remove('hidden');
                }
            });
            // If store keeper is on a restricted tab, kick them back to POS
            if (role === 'Store Keeper') {
                const activeTab = document.querySelector('.tab-content:not(.hidden)').id;
                if (activeTab === 'content-expenses' || activeTab === 'content-reports') {
                    switchTab('pos');
                }
            }
        }

        function switchTab(tabId) {
            if (currentRole === 'Store Keeper' && (tabId === 'expenses' || tabId === 'reports')) {
                alert('Access Restricted: Store Keepers cannot view financial reports or expenses.');
                return;
            }
            document.querySelectorAll('.tab-content').forEach(el => el.classList.add('hidden'));
            document.querySelectorAll('.tab-btn').forEach(el => {
                el.classList.remove('bg-blue-600', 'text-white', 'shadow');
                el.classList.add('text-gray-400');
            });
            document.getElementById('content-' + tabId).classList.remove('hidden');
            const btn = document.getElementById('tab-' + tabId);
            btn.classList.add('bg-blue-600', 'text-white', 'shadow');
            btn.classList.remove('text-gray-400');

            if (tabId === 'inventory') fetchInventory();
            if (tabId === 'expenses') fetchExpenses();
            if (tabId === 'reports') fetchReports();
        }

        async function fetchInventory() {
            const res = await fetch('/api/inventory');
            inventory = await res.json();
            renderPOSGrid();
            renderInventoryTable();
        }

        function renderPOSGrid() {
            const grid = document.getElementById('posGrid');
            const search = document.getElementById('posSearch').value.toLowerCase();
            grid.innerHTML = '';
            inventory.filter(i => i.name.toLowerCase().includes(search)).forEach(item => {
                grid.innerHTML += `
                    <div onclick="addToCart(${item.id})" class="obsidian-card p-4 rounded-xl cursor-pointer hover:border-blue-500 transition flex flex-col justify-between">
                        <div>
                            <span class="text-xs bg-gray-800 text-gray-300 px-2 py-0.5 rounded">${item.category}</span>
                            <h4 class="font-bold text-white mt-2 text-sm">${item.name}</h4>
                        </div>
                        <div class="mt-4 flex justify-between items-end">
                            <div>
                                <p class="text-xs text-gray-400">Stock: ${item.stock} ${item.unit}</p>
                                <p class="text-blue-400 font-bold text-base">₱${item.selling_price.toFixed(2)}</p>
                            </div>
                            <button class="bg-blue-600 text-white w-8 h-8 rounded-lg flex items-center justify-center font-bold">+</button>
                        </div>
                    </div>
                `;
            });
        }

        function filterPOSItems() { renderPOSGrid(); }

        function addToCart(id) {
            const item = inventory.find(i => i.id === id);
            if (!item || item.stock <= 0) {
                alert('Item is out of stock!');
                return;
            }
            const existing = cart.find(c => c.id === id);
            if (existing) {
                if (existing.qty < item.stock) {
                    existing.qty++;
                } else {
                    alert('Reached maximum available stock!');
                }
            } else {
                cart.push({ id: item.id, name: item.name, price: item.selling_price, qty: 1, unit: item.unit });
            }
            renderCart();
        }

        function renderCart() {
            const container = document.getElementById('cartItems');
            container.innerHTML = '';
            if (cart.length === 0) {
                container.innerHTML = '<p class="text-gray-500 text-sm text-center py-10">Cart is empty</p>';
                document.getElementById('cartCount').innerText = '0';
                document.getElementById('cartTotal').innerText = '₱0.00';
                return;
            }
            let total = 0;
            let count = 0;
            cart.forEach((c, idx) => {
                total += c.price * c.qty;
                count += c.qty;
                container.innerHTML += `
                    <div class="flex justify-between items-center bg-obsidian-800 p-3 rounded-xl border border-gray-700 text-sm">
                        <div>
                            <h5 class="font-semibold text-white">${c.name}</h5>
                            <p class="text-xs text-blue-400">₱${c.price.toFixed(2)} x ${c.qty}</p>
                        </div>
                        <div class="flex items-center space-x-2">
                            <button onclick="changeQty(${idx}, 1)" class="bg-gray-700 px-2 py-0.5 rounded text-white font-bold">+</button>
                            <button onclick="changeQty(${idx}, -1)" class="bg-gray-700 px-2 py-0.5 rounded text-white font-bold">-</button>
                        </div>
                    </div>
                `;
            });
            document.getElementById('cartCount').innerText = count;
            document.getElementById('cartTotal').innerText = '₱' + total.toFixed(2);
        }

        function changeQty(idx, delta) {
            cart[idx].qty += delta;
            if (cart[idx].qty <= 0) {
                cart.splice(idx, 1);
            }
            renderCart();
        }

        function clearCart() {
            cart = [];
            renderCart();
        }

        async function checkout() {
            if (cart.length === 0) return alert('Cart is empty!');
            const payload = {
                items: JSON.stringify(cart),
                total: cart.reduce((sum, i) => sum + (i.price * i.qty), 0),
                payment_method: document.getElementById('paymentMethod').value,
                cashier: currentRole
            };
            const res = await fetch('/api/sales', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(payload)
            });
            const result = await res.json();
            if (result.success) {
                showReceipt(payload);
                clearCart();
                fetchInventory();
            } else {
                alert('Checkout failed: ' + result.error);
            }
        }

        function showReceipt(sale) {
            document.getElementById('receiptDate').innerText = new Date().toLocaleString();
            document.getElementById('receiptTotal').innerText = '₱' + sale.total.toFixed(2);
            document.getElementById('receiptMethod').innerText = 'Method: ' + sale.payment_method;
            document.getElementById('receiptCashier').innerText = 'Cashier: ' + sale.cashier;
            const body = document.getElementById('receiptBody');
            body.innerHTML = '';
            JSON.parse(sale.items).forEach(i => {
                body.innerHTML += `
                    <div class="flex justify-between text-xs">
                        <span>${i.qty}x ${i.name}</span>
                        <span>₱${(i.price * i.qty).toFixed(2)}</span>
                    </div>
                `;
            });
            document.getElementById('receiptModal').classList.remove('hidden');
        }

        function closeReceiptModal() {
            document.getElementById('receiptModal').classList.add('hidden');
        }

        // Calculators
        function calculateRice() {
            const cost = parseFloat(document.getElementById('riceSackCost').value) || 0;
            const weight = parseFloat(document.getElementById('riceSackWeight').value) || 1;
            const retail = parseFloat(document.getElementById('riceRetailPerKilo').value) || 0;
            const costPerKilo = cost / weight;
            const totalRev = retail * weight;
            const profit = totalRev - cost;

            document.getElementById('resCostPerKilo').innerText = '₱' + costPerKilo.toFixed(2);
            document.getElementById('resTotalRev').innerText = '₱' + totalRev.toFixed(2);
            document.getElementById('resTotalProfit').innerText = '₱' + profit.toFixed(2);
        }

        function calculateBox() {
            const cost = parseFloat(document.getElementById('boxCost').value) || 0;
            const units = parseFloat(document.getElementById('boxUnits').value) || 1;
            const markup = parseFloat(document.getElementById('boxMarkup').value) || 0;
            const costPerUnit = cost / units;
            const sellingPerUnit = costPerUnit * (1 + (markup / 100));

            document.getElementById('boxCostPerUnit').innerText = '₱' + costPerUnit.toFixed(2);
            document.getElementById('boxSellingPerUnit').innerText = '₱' + sellingPerUnit.toFixed(2);
        }

        // Inventory Management
        function renderInventoryTable() {
            const tbody = document.getElementById('inventoryTable');
            const search = document.getElementById('invSearch').value.toLowerCase();
            tbody.innerHTML = '';
            inventory.filter(i => i.name.toLowerCase().includes(search)).forEach(i => {
                const actionButtons = currentRole === 'Admin' ? `
                    <button onclick="editProduct(${i.id})" class="text-blue-400 hover:underline mr-3">Edit</button>
                    <button onclick="deleteProduct(${i.id})" class="text-red-400 hover:underline">Delete</button>
                ` : `<span class="text-gray-500 text-xs">Locked</span>`;

                tbody.innerHTML += `
                    <tr class="border-b border-gray-800 hover:bg-obsidian-800/50">
                        <td class="p-4 font-medium text-white">${i.name}</td>
                        <td class="p-4 text-gray-400">${i.category}</td>
                        <td class="p-4">₱${i.cost_price.toFixed(2)}</td>
                        <td class="p-4 text-blue-400">₱${i.selling_price.toFixed(2)}</td>
                        <td class="p-4">${i.stock} ${i.unit}</td>
                        <td class="p-4 text-right admin-only">${actionButtons}</td>
                    </tr>
                `;
            });
            switchRole(currentRole); // Re-apply visibility lock
        }

        function filterInventory() { renderInventoryTable(); }

        function openAddModal() {
            if (currentRole !== 'Admin') return alert('Restricted to Admin');
            document.getElementById('productModalTitle').innerText = 'Add New Product';
            document.getElementById('prodId').value = '';
            document.getElementById('prodName').value = '';
            document.getElementById('prodCategory').value = '';
            document.getElementById('prodUnit').value = 'pcs';
            document.getElementById('prodCost').value = '';
            document.getElementById('prodPrice').value = '';
            document.getElementById('prodStock').value = '';
            document.getElementById('productModal').classList.remove('hidden');
        }

        function editProduct(id) {
            if (currentRole !== 'Admin') return alert('Restricted to Admin');
            const item = inventory.find(i => i.id === id);
            document.getElementById('productModalTitle').innerText = 'Edit Product';
            document.getElementById('prodId').value = item.id;
            document.getElementById('prodName').value = item.name;
            document.getElementById('prodCategory').value = item.category;
            document.getElementById('prodUnit').value = item.unit;
            document.getElementById('prodCost').value = item.cost_price;
            document.getElementById('prodPrice').value = item.selling_price;
            document.getElementById('prodStock').value = item.stock;
            document.getElementById('productModal').classList.remove('hidden');
        }

        function closeProductModal() {
            document.getElementById('productModal').classList.add('hidden');
        }

        async function saveProduct() {
            const id = document.getElementById('prodId').value;
            const payload = {
                name: document.getElementById('prodName').value,
                category: document.getElementById('prodCategory').value,
                unit: document.getElementById('prodUnit').value,
                cost_price: parseFloat(document.getElementById('prodCost').value),
                selling_price: parseFloat(document.getElementById('prodPrice').value),
                stock: parseInt(document.getElementById('prodStock').value)
            };
            const method = id ? 'PUT' : 'POST';
            const url = id ? `/api/inventory?id=${id}` : '/api/inventory';
            await fetch(url, { method, headers: {'Content-Type': 'application/json'}, body: JSON.stringify(payload) });
            closeProductModal();
            fetchInventory();
        }

        async function deleteProduct(id) {
            if (currentRole !== 'Admin') return alert('Restricted to Admin');
            if (confirm('Are you sure you want to delete this product?')) {
                await fetch(`/api/inventory?id=${id}`, { method: 'DELETE' });
                fetchInventory();
            }
        }

        // Expenses
        function openExpenseModal() {
            if (currentRole !== 'Admin') return alert('Restricted to Admin');
            document.getElementById('expCategory').value = '';
            document.getElementById('expAmount').value = '';
            document.getElementById('expNotes').value = '';
            document.getElementById('expenseModal').classList.remove('hidden');
        }
        function closeExpenseModal() { document.getElementById('expenseModal').classList.add('hidden'); }

        async function saveExpense() {
            const payload = {
                category: document.getElementById('expCategory').value,
                amount: parseFloat(document.getElementById('expAmount').value),
                notes: document.getElementById('expNotes').value
            };
            await fetch('/api/expenses', { method: 'POST', headers: {'Content-Type': 'application/json'}, body: JSON.stringify(payload) });
            closeExpenseModal();
            fetchExpenses();
        }

        async function fetchExpenses() {
            const res = await fetch('/api/expenses');
            const data = await res.json();
            const tbody = document.getElementById('expensesTable');
            tbody.innerHTML = '';
            data.forEach(e => {
                tbody.innerHTML += `
                    <tr class="border-b border-gray-800">
                        <td class="p-4 text-gray-400">${e.date}</td>
                        <td class="p-4 font-semibold text-white">${e.category}</td>
                        <td class="p-4 text-red-400">₱${e.amount.toFixed(2)}</td>
                        <td class="p-4 text-gray-300">${e.notes || '-'}</td>
                        <td class="p-4 text-right"><button onclick="deleteExpense(${e.id})" class="text-red-400 hover:underline text-xs">Delete</button></td>
                    </tr>
                `;
            });
        }

        async function deleteExpense(id) {
            if (confirm('Delete expense?')) {
                await fetch(`/api/expenses?id=${id}`, { method: 'DELETE' });
                fetchExpenses();
            }
        }

        // Reports
        async function fetchReports() {
            const salesRes = await fetch('/api/sales');
            const sales = await salesRes.json();
            const expRes = await fetch('/api/expenses');
            const expenses = await expRes.json();

            let totalRev = sales.reduce((sum, s) => sum + s.total, 0);
            let totalExp = expenses.reduce((sum, e) => sum + e.amount, 0);
            let net = totalRev - totalExp;

            document.getElementById('repRevenue').innerText = '₱' + totalRev.toFixed(2);
            document.getElementById('repExpenses').innerText = '₱' + totalExp.toFixed(2);
            document.getElementById('repNetProfit').innerText = '₱' + net.toFixed(2);

            const tbody = document.getElementById('salesReportTable');
            tbody.innerHTML = '';
            sales.forEach(s => {
                tbody.innerHTML += `
                    <tr class="border-b border-gray-800">
                        <td class="p-3 text-gray-400">#${s.id}</td>
                        <td class="p-3 text-gray-400">${s.date}</td>
                        <td class="p-3 text-xs text-gray-300">items</td>
                        <td class="p-3"><span class="bg-gray-800 px-2 py-0.5 rounded text-xs">${s.payment_method}</span></td>
                        <td class="p-3 text-gray-400">${s.cashier}</td>
                        <td class="p-3 text-right font-bold text-blue-400">₱${s.total.toFixed(2)}</td>
                    </tr>
                `;
            });
        }

        // Initialize App on load
        window.onload = () => {
            fetchInventory();
            calculateRice();
            calculateBox();
        };
    </script>
</body>
</html>
"""

class VaultHandler(http.server.SimpleHTTPRequestHandler):
    def do_GET(self):
        parsed_path = urllib.parse.urlparse(self.path)
        path = parsed_path.path
        query = urllib.parse.parse_qs(parsed_path.query)

        if path == "/" or path == "":
            self.send_response(200)
            self.send_header("Content-Type", "text/html")
            self.end_headers()
            self.wfile.write(HTML_TEMPLATE.encode("utf-8"))
        elif path == "/api/inventory":
            conn = sqlite3.connect(DB_FILE)
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM inventory")
            items = [dict(row) for row in cursor.fetchall()]
            conn.close()
            self.send_json(items)
        elif path == "/api/sales":
            conn = sqlite3.connect(DB_FILE)
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM sales ORDER BY id DESC")
            sales = [dict(row) for row in cursor.fetchall()]
            conn.close()
            self.send_json(sales)
        elif path == "/api/expenses":
            conn = sqlite3.connect(DB_FILE)
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM expenses ORDER BY id DESC")
            expenses = [dict(row) for row in cursor.fetchall()]
            conn.close()
            self.send_json(expenses)
        else:
            super().do_GET()

    def do_POST(self):
        parsed_path = urllib.parse.urlparse(self.path)
        path = parsed_path.path
        length = int(self.headers.get('content-length', 0))
        body = json.loads(self.rfile.read(length).decode('utf-8')) if length > 0 else {}

        if path == "/api/inventory":
            conn = sqlite3.connect(DB_FILE)
            cursor = conn.cursor()
            cursor.execute("INSERT INTO inventory (name, category, cost_price, selling_price, stock, unit) VALUES (?, ?, ?, ?, ?, ?)",
                           (body.get('name'), body.get('category'), body.get('cost_price'), body.get('selling_price'), body.get('stock'), body.get('unit')))
            conn.commit()
            conn.close()
            self.send_json({"success": True})
        elif path == "/api/sales":
            conn = sqlite3.connect(DB_FILE)
            cursor = conn.cursor()
            date_str = datetime.now().strftime("%Y-%m-%d %H:%M")
            items = body.get('items', '[]')
            total = body.get('total', 0)
            payment = body.get('payment_method', 'Cash')
            cashier = body.get('cashier', 'Admin')
            
            # Deduct stock
            parsed_items = json.loads(items)
            for pi in parsed_items:
                cursor.execute("UPDATE inventory SET stock = stock - ? WHERE id = ?", (pi['qty'], pi['id']))

            cursor.execute("INSERT INTO sales (date, items, total, payment_method, cashier) VALUES (?, ?, ?, ?, ?)",
                           (date_str, items, total, payment, cashier))
            conn.commit()
            conn.close()
            self.send_json({"success": True})
        elif path == "/api/expenses":
            conn = sqlite3.connect(DB_FILE)
            cursor = conn.cursor()
            date_str = datetime.now().strftime("%Y-%m-%d")
            cursor.execute("INSERT INTO expenses (date, category, amount, notes) VALUES (?, ?, ?, ?)",
                           (date_str, body.get('category'), body.get('amount'), body.get('notes')))
            conn.commit()
            conn.close()
            self.send_json({"success": True})
        else:
            self.send_response(404)
            self.end_headers()

    def do_PUT(self):
        parsed_path = urllib.parse.urlparse(self.path)
        path = parsed_path.path
        query = urllib.parse.parse_qs(parsed_path.query)
        length = int(self.headers.get('content-length', 0))
        body = json.loads(self.rfile.read(length).decode('utf-8')) if length > 0 else {}

        if path == "/api/inventory" and 'id' in query:
            item_id = query['id'][0]
            conn = sqlite3.connect(DB_FILE)
            cursor = conn.cursor()
            cursor.execute("UPDATE inventory SET name=?, category=?, cost_price=?, selling_price=?, stock=?, unit=? WHERE id=?",
                           (body.get('name'), body.get('category'), body.get('cost_price'), body.get('selling_price'), body.get('stock'), body.get('unit'), item_id))
            conn.commit()
            conn.close()
            self.send_json({"success": True})

    def do_DELETE(self):
        parsed_path = urllib.parse.urlparse(self.path)
        path = parsed_path.path
        query = urllib.parse.parse_qs(parsed_path.query)

        if path == "/api/inventory" and 'id' in query:
            item_id = query['id'][0]
            conn = sqlite3.connect(DB_FILE)
            cursor = conn.cursor()
            cursor.execute("DELETE FROM inventory WHERE id=?", (item_id,))
            conn.commit()
            conn.close()
            self.send_json({"success": True})
        elif path == "/api/expenses" and 'id' in query:
            exp_id = query['id'][0]
            conn = sqlite3.connect(DB_FILE)
            cursor = conn.cursor()
            cursor.execute("DELETE FROM expenses WHERE id=?", (exp_id,))
            conn.commit()
            conn.close()
            self.send_json({"success": True})

    def send_json(self, data):
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.end_headers()
        self.wfile.write(json.dumps(data).encode("utf-8"))

if __name__ == "__main__":
    with socketserver.TCPServer(("", PORT), VaultHandler) as httpd:
        print(f"Serving Ibañez Vault Store App on port {PORT}")
        httpd.serve_forever()
