# -*- coding: utf-8 -*-
import http.server
import socketserver
import webbrowser
import threading
import socket
import json
import time
from datetime import datetime

PORT = 8090

def get_local_ip():
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        s.connect(('10.255.255.255', 1))
        IP = s.getsockname()[0]
    except Exception:
        IP = '127.0.0.1'
    finally:
        s.close()
    return IP

LOCAL_IP = get_local_ip()

HTML_CONTENT = r"""<!DOCTYPE html>
<html lang="en" id="html-root" class="dark">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Ibañez Store - Obsidian Vault POS & Ledger</title>
    <script src="https://cdn.tailwindcss.com"></script>
    <script src="https://cdnjs.cloudflare.com/ajax/libs/html2canvas/1.4.1/html2canvas.min.js"></script>
    <script>
        tailwind.config = {
            darkMode: 'class',
            theme: {
                extend: {
                    colors: {
                        obsidianDark: '#12151C',
                        obsidianCard: '#1E2330',
                        obsidianBorder: '#323B4D',
                        obsidianLight: '#E8ECF2',
                        obsidianLightCard: '#FFFFFF',
                        obsidianLightBorder: '#CBD5E1'
                    }
                }
            }
        }
    </script>
    <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/css/all.min.css">
    <style>
        ::-webkit-scrollbar { width: 4px; height: 4px; }
        ::-webkit-scrollbar-thumb { background: #323B4D; border-radius: 9999px; }
        .no-scrollbar::-webkit-scrollbar { display: none; }
        .no-scrollbar { -ms-overflow-style: none; scrollbar-width: none; }

        .obsidian-key {
            border: 2px solid var(--key-border);
            box-shadow: 0 4px 0 var(--key-shadow);
            transition: all 0.08s ease;
            position: relative;
        }
        .obsidian-key:hover {
            transform: translateY(-1px);
            box-shadow: 0 5px 0 var(--key-shadow);
        }
        .obsidian-key:active {
            transform: translateY(3px);
            box-shadow: 0 1px 0 var(--key-shadow);
        }

        .dark {
            --key-border: #3A4459;
            --key-shadow: #0A0D14;
            --card-bg: #1E2330;
            --bg-main: #12151C;
        }
        html:not(.dark) {
            --key-border: #94A3B8;
            --key-shadow: #64748B;
            --card-bg: #FFFFFF;
            --bg-main: #F1F5F9;
        }
    </style>
</head>
<body class="bg-slate-100 dark:bg-obsidianDark text-slate-900 dark:text-obsidianLight min-h-screen flex flex-col font-sans relative pb-32 transition-colors duration-300">

    <!-- LOGIN MODAL -->
    <div id="login-modal" class="fixed inset-0 z-50 bg-slate-950/90 dark:bg-[#12151C]/95 flex items-center justify-center p-4">
        <div class="bg-white dark:bg-obsidianCard border-2 border-slate-300 dark:border-obsidianBorder rounded-3xl w-full max-w-sm p-6 space-y-5 shadow-2xl text-center obsidian-key">
            <div class="w-16 h-16 bg-indigo-600 rounded-2xl flex items-center justify-center mx-auto text-white text-3xl shadow-lg shadow-indigo-500/20">
                <i class="fa-solid fa-vault"></i>
            </div>
            <div>
                <h2 class="text-2xl font-black tracking-tight">Ibañez Vault Store</h2>
                <p class="text-xs text-slate-500 dark:text-slate-400 mt-1">Obsidian POS & Ledger System</p>
            </div>
            <div class="space-y-3.5 text-left">
                <div>
                    <label class="text-slate-600 dark:text-slate-400 text-[11px] font-bold block mb-1 uppercase tracking-wider">Select Role</label>
                    <select id="login-role" class="w-full bg-slate-100 dark:bg-[#12151C] border-2 border-slate-300 dark:border-obsidianBorder rounded-xl px-3.5 py-2.5 text-sm font-medium focus:outline-none focus:border-indigo-500">
                        <option value="Admin">Admin / Vault Owner</option>
                        <option value="Store Keeper">Store Keeper</option>
                    </select>
                </div>
                <div>
                    <label class="text-slate-600 dark:text-slate-400 text-[11px] font-bold block mb-1 uppercase tracking-wider">Password</label>
                    <div class="relative flex items-center">
                        <input type="password" id="login-pass" autocomplete="new-password" placeholder="Enter password" class="w-full bg-slate-100 dark:bg-[#12151C] border-2 border-slate-300 dark:border-obsidianBorder rounded-xl pl-3.5 pr-10 py-2.5 text-sm font-medium focus:outline-none focus:border-indigo-500">
                        <button type="button" onclick="togglePasswordVisibility()" class="absolute right-3 text-slate-400 hover:text-slate-200 focus:outline-none">
                            <i id="pass-toggle-icon" class="fa-solid fa-eye"></i>
                        </button>
                    </div>
                </div>
                <div id="login-error" class="hidden text-xs text-rose-500 font-bold text-center">
                    Incorrect password! Please try again.
                </div>
            </div>
            <button onclick="performLogin()" class="w-full bg-indigo-600 hover:bg-indigo-500 text-white font-bold py-3.5 rounded-xl text-xs obsidian-key flex items-center justify-center gap-2">
                <i class="fa-solid fa-key"></i> Unlock Vault
            </button>
        </div>
    </div>

    <!-- TOAST NOTIFICATION -->
    <div id="top-toast" class="fixed top-3 left-1/2 -translate-x-1/2 z-50 hidden transition-all duration-300">
        <div id="top-toast-body" class="bg-indigo-600 text-white px-6 py-3 rounded-2xl shadow-2xl font-black text-sm border-2 border-indigo-400 flex items-center justify-center gap-2">
            <span id="top-toast-msg">Success</span>
        </div>
    </div>

    <!-- CHECKOUT & TRANSACTION RECEIPT MODAL -->
    <div id="receipt-modal" class="fixed inset-0 z-50 bg-black/80 backdrop-blur-sm hidden flex flex-col items-center justify-center p-4 overflow-y-auto">
        <div id="receipt-card-content" class="bg-white dark:bg-obsidianCard border-2 border-indigo-500/50 rounded-3xl w-full max-w-sm p-6 space-y-4 shadow-2xl obsidian-key text-center">
            <div class="border-b-2 border-dashed border-slate-300 dark:border-obsidianBorder pb-3 space-y-1">
                <div class="w-12 h-12 bg-indigo-600 text-white rounded-2xl flex items-center justify-center mx-auto text-xl shadow-md">
                    <i class="fa-solid fa-store"></i>
                </div>
                <h3 class="text-lg font-black tracking-wider uppercase text-indigo-400">Ibañez Store</h3>
                <p class="text-[10px] text-slate-400 font-medium">Official Transaction Receipt</p>
                <div class="text-[10px] text-slate-400 font-bold pt-1 flex justify-between">
                    <span id="rcpt-id">TX-000</span>
                    <span id="rcpt-date">2026-10-20 | 00:00:00</span>
                </div>
            </div>

            <div class="text-left bg-slate-100 dark:bg-[#12151C] p-2.5 rounded-xl border border-slate-300 dark:border-obsidianBorder flex justify-between items-center text-xs">
                <span class="text-slate-400 font-bold uppercase tracking-wider text-[10px]">Customer:</span>
                <span class="font-black text-indigo-400" id="rcpt-customer">Walk-in Customer</span>
            </div>

            <div class="space-y-2 text-xs text-left max-h-56 overflow-y-auto pr-1">
                <div class="flex justify-between font-black text-[10px] text-slate-400 border-b border-slate-200 dark:border-obsidianBorder pb-1 uppercase">
                    <span>ITEMS & DESCRIPTION</span>
                    <span class="text-right">AMOUNT</span>
                </div>
                <div id="rcpt-items-breakdown" class="space-y-1.5 font-medium"></div>
            </div>

            <div class="bg-slate-100 dark:bg-[#12151C] border-2 border-slate-300 dark:border-obsidianBorder rounded-2xl p-4 space-y-2 text-xs text-left">
                <div class="flex justify-between"><span class="text-slate-400 font-bold">Payment Method:</span><span class="font-black text-emerald-400" id="rcpt-type">Paid (Cash)</span></div>
                <div class="flex justify-between"><span class="text-slate-400 font-bold">Total Bill:</span><span class="font-black text-base" id="rcpt-total">₱0</span></div>
                <div class="flex justify-between"><span class="text-slate-400 font-bold">Cash Received:</span><span class="font-bold text-indigo-400" id="rcpt-cash">₱0</span></div>
                <div class="flex justify-between pt-2 border-t border-dashed border-slate-300 dark:border-obsidianBorder"><span class="font-black text-slate-300">Change Due:</span><span class="font-black text-lg text-emerald-400" id="rcpt-change">₱0</span></div>
            </div>

            <p class="text-[10px] text-slate-400 italic font-medium">Thank you for shopping with us!</p>
        </div>

        <div class="w-full max-w-sm mt-3 grid grid-cols-2 gap-2">
            <button onclick="saveReceiptToGallery()" class="w-full bg-emerald-500 hover:bg-emerald-400 text-slate-950 font-black py-3 px-2 rounded-xl text-[11px] obsidian-key shadow-lg flex items-center justify-center gap-1.5">
                <i class="fa-solid fa-download"></i> Save Gallery
            </button>
            <button onclick="closeReceiptModal()" class="w-full bg-indigo-600 hover:bg-indigo-500 text-white font-black py-3 px-2 rounded-xl text-[11px] obsidian-key shadow-lg flex items-center justify-center gap-1.5">
                <i class="fa-solid fa-check"></i> Close
            </button>
        </div>
    </div>

    <!-- RICE RESELLER PRICING CALCULATOR MODAL -->
    <div id="rice-calc-modal" class="fixed inset-0 z-50 bg-black/80 backdrop-blur-sm hidden flex items-center justify-center p-4">
        <div class="bg-white dark:bg-obsidianCard border-2 border-slate-300 dark:border-obsidianBorder rounded-3xl w-full max-w-md p-5 space-y-4 shadow-2xl obsidian-key">
            <div class="flex justify-between items-center pb-2 border-b border-slate-200 dark:border-obsidianBorder">
                <h3 class="font-extrabold text-base flex items-center gap-2 text-amber-400">
                    <i class="fa-solid fa-wheat-awn"></i> Rice Reseller Pricing Calculator
                </h3>
                <button onclick="closeRiceCalcModal()" class="text-slate-400 hover:text-white"><i class="fa-solid fa-xmark text-base"></i></button>
            </div>
            
            <div class="space-y-3 text-xs">
                <div>
                    <label class="block mb-1 font-bold text-slate-400">Rice Variety / Name</label>
                    <input type="text" id="rc-name" value="JASMINE SPECIAL" class="w-full bg-slate-100 dark:bg-[#12151C] border-2 border-slate-300 dark:border-obsidianBorder rounded-xl px-3.5 py-2 font-bold">
                </div>

                <div class="grid grid-cols-2 gap-3">
                    <div>
                        <label class="block mb-1 font-bold text-slate-400">Sack Cost (₱)</label>
                        <input type="number" id="rc-sack-cost" value="2300" oninput="calcRiceFormula()" class="w-full bg-slate-100 dark:bg-[#12151C] border-2 border-slate-300 dark:border-obsidianBorder rounded-xl px-3 py-2 font-bold">
                    </div>
                    <div>
                        <label class="block mb-1 font-bold text-slate-400">Weight (KG)</label>
                        <input type="number" id="rc-weight" value="50" oninput="calcRiceFormula()" class="w-full bg-slate-100 dark:bg-[#12151C] border-2 border-slate-300 dark:border-obsidianBorder rounded-xl px-3 py-2 font-bold">
                    </div>
                </div>

                <div class="grid grid-cols-2 gap-3">
                    <div>
                        <label class="block mb-1 font-bold text-slate-400">Spill / Loss (KG)</label>
                        <input type="number" id="rc-spill" value="1.0" step="0.1" oninput="calcRiceFormula()" class="w-full bg-slate-100 dark:bg-[#12151C] border-2 border-slate-300 dark:border-obsidianBorder rounded-xl px-3 py-2 font-bold">
                    </div>
                    <div>
                        <label class="block mb-1 font-bold text-slate-400">Transport Cost (₱)</label>
                        <input type="number" id="rc-transport" value="50" oninput="calcRiceFormula()" class="w-full bg-slate-100 dark:bg-[#12151C] border-2 border-slate-300 dark:border-obsidianBorder rounded-xl px-3 py-2 font-bold">
                    </div>
                </div>

                <div class="grid grid-cols-2 gap-3">
                    <div>
                        <label class="block mb-1 font-bold text-slate-400">Plastic Packaging/KG (₱)</label>
                        <input type="number" id="rc-packaging" value="0.5" step="0.1" oninput="calcRiceFormula()" class="w-full bg-slate-100 dark:bg-[#12151C] border-2 border-slate-300 dark:border-obsidianBorder rounded-xl px-3 py-2 font-bold">
                    </div>
                    <div>
                        <label class="block mb-1 font-bold text-slate-400">Target Margin (%)</label>
                        <input type="number" id="rc-margin" value="20" oninput="calcRiceFormula()" class="w-full bg-slate-100 dark:bg-[#12151C] border-2 border-slate-300 dark:border-obsidianBorder rounded-xl px-3 py-2 font-bold">
                    </div>
                </div>

                <div class="bg-slate-100 dark:bg-[#12151C] border-2 border-slate-300 dark:border-obsidianBorder rounded-2xl p-4 space-y-2 font-medium">
                    <div class="flex justify-between"><span class="text-slate-400 font-bold">Net Saleable Weight:</span><span class="font-black" id="rc-out-netweight">49.0 KG</span></div>
                    <div class="flex justify-between"><span class="text-slate-400 font-bold">Total Capital:</span><span class="font-black" id="rc-out-capital">₱2350.00</span></div>
                    <div class="flex justify-between"><span class="text-slate-400 font-bold">Actual Cost / KG:</span><span class="font-black" id="rc-out-actualcost">₱48.46</span></div>
                    <div class="flex justify-between pt-2 border-t border-slate-300 dark:border-obsidianBorder"><span class="font-black text-emerald-400">Rec. Selling Price / KG:</span><span class="font-black text-emerald-400 text-base" id="rc-out-recprice">₱60.57</span></div>
                </div>

                <div>
                    <label class="block mb-1 font-bold text-slate-400 uppercase text-[10px]">Import Option</label>
                    <select id="rc-import-opt" class="w-full bg-slate-100 dark:bg-[#12151C] border-2 border-slate-300 dark:border-obsidianBorder rounded-xl px-3.5 py-2.5 font-bold">
                        <option value="both">Import Both (Per KG & Whole Sack)</option>
                        <option value="kg">Import Per KG Only</option>
                        <option value="sack">Import Whole Sack Only</option>
                    </select>
                </div>
            </div>

            <div class="flex gap-2 pt-2">
                <button onclick="closeRiceCalcModal()" class="flex-1 bg-slate-200 dark:bg-obsidianBorder font-bold py-3 rounded-xl text-xs obsidian-key">Cancel</button>
                <button onclick="importRiceToInventory()" class="flex-1 bg-emerald-500 hover:bg-emerald-400 text-slate-950 font-black py-3 rounded-xl text-xs obsidian-key shadow-lg">Import To Inventory</button>
            </div>
        </div>
    </div>

    <!-- BULK CASE / BOX PRICING CALCULATOR MODAL -->
    <div id="bulk-calc-modal" class="fixed inset-0 z-50 bg-black/80 backdrop-blur-sm hidden flex items-center justify-center p-4">
        <div class="bg-white dark:bg-obsidianCard border-2 border-slate-300 dark:border-obsidianBorder rounded-3xl w-full max-w-md p-5 space-y-4 shadow-2xl obsidian-key">
            <div class="flex justify-between items-center pb-2 border-b border-slate-200 dark:border-obsidianBorder">
                <h3 class="font-extrabold text-base flex items-center gap-2 text-indigo-400">
                    <i class="fa-solid fa-boxes-packing"></i> Bulk Case / Box Pricing Calculator
                </h3>
                <button onclick="closeBulkCalcModal()" class="text-slate-400 hover:text-white"><i class="fa-solid fa-xmark text-base"></i></button>
            </div>

            <div class="space-y-3 text-xs">
                <div>
                    <label class="block mb-1 font-bold text-slate-400">Item Name</label>
                    <input type="text" id="bc-name" value="Coca-Cola 1.5L (Case of 12)" class="w-full bg-slate-100 dark:bg-[#12151C] border-2 border-slate-300 dark:border-obsidianBorder rounded-xl px-3.5 py-2 font-bold">
                </div>

                <div class="grid grid-cols-2 gap-3">
                    <div>
                        <label class="block mb-1 font-bold text-slate-400">Case / Box Cost (₱)</label>
                        <input type="number" id="bc-box-cost" value="650" oninput="calcBulkFormula()" class="w-full bg-slate-100 dark:bg-[#12151C] border-2 border-slate-300 dark:border-obsidianBorder rounded-xl px-3 py-2 font-bold">
                    </div>
                    <div>
                        <label class="block mb-1 font-bold text-slate-400">Units per Box</label>
                        <input type="number" id="bc-units" value="12" oninput="calcBulkFormula()" class="w-full bg-slate-100 dark:bg-[#12151C] border-2 border-slate-300 dark:border-obsidianBorder rounded-xl px-3 py-2 font-bold">
                    </div>
                </div>

                <div class="grid grid-cols-2 gap-3">
                    <div>
                        <label class="block mb-1 font-bold text-slate-400">Freight / Delivery (₱)</label>
                        <input type="number" id="bc-freight" value="30" oninput="calcBulkFormula()" class="w-full bg-slate-100 dark:bg-[#12151C] border-2 border-slate-300 dark:border-obsidianBorder rounded-xl px-3 py-2 font-bold">
                    </div>
                    <div>
                        <label class="block mb-1 font-bold text-slate-400">Target Margin (%)</label>
                        <input type="number" id="bc-margin" value="25" oninput="calcBulkFormula()" class="w-full bg-slate-100 dark:bg-[#12151C] border-2 border-slate-300 dark:border-obsidianBorder rounded-xl px-3 py-2 font-bold">
                    </div>
                </div>

                <div class="bg-slate-100 dark:bg-[#12151C] border-2 border-slate-300 dark:border-obsidianBorder rounded-2xl p-4 space-y-2 font-medium">
                    <div class="flex justify-between"><span class="text-slate-400 font-bold">Total Box Cost:</span><span class="font-black" id="bc-out-boxcost">₱680.00</span></div>
                    <div class="flex justify-between"><span class="text-slate-400 font-bold">Individual Unit Cost:</span><span class="font-black" id="bc-out-unitcost">₱56.67</span></div>
                    <div class="flex justify-between pt-2 border-t border-slate-300 dark:border-obsidianBorder"><span class="font-black text-emerald-400">Rec. Selling Unit Price:</span><span class="font-black text-emerald-400 text-base" id="bc-out-recprice">₱75.56</span></div>
                </div>
            </div>

            <div class="flex gap-2 pt-2">
                <button onclick="closeBulkCalcModal()" class="flex-1 bg-slate-200 dark:bg-obsidianBorder font-bold py-3 rounded-xl text-xs obsidian-key">Cancel</button>
                <button onclick="importBulkToInventory()" class="flex-1 bg-indigo-600 hover:bg-indigo-500 text-white font-black py-3 rounded-xl text-xs obsidian-key shadow-lg">Import To Inventory</button>
            </div>
        </div>
    </div>

    <!-- FORMULA INFO MODAL -->
    <div id="formula-modal" class="fixed inset-0 z-50 bg-black/70 backdrop-blur-sm hidden flex items-center justify-center p-4">
        <div class="bg-white dark:bg-obsidianCard border-2 border-slate-300 dark:border-obsidianBorder rounded-3xl w-full max-w-sm p-5 space-y-4 shadow-2xl obsidian-key">
            <div class="flex justify-between items-center pb-2 border-b border-slate-200 dark:border-obsidianBorder">
                <h3 class="font-bold text-base flex items-center gap-2" id="formula-modal-title">
                    <i class="fa-solid fa-circle-info text-indigo-500"></i> Formula Info
                </h3>
                <button onclick="closeFormulaModal()" class="text-slate-400 hover:text-white"><i class="fa-solid fa-xmark text-base"></i></button>
            </div>
            <div class="space-y-3 text-xs">
                <p class="text-slate-600 dark:text-slate-300 font-medium leading-relaxed" id="formula-modal-desc">Formula breakdown details.</p>
                <div class="p-3 bg-slate-100 dark:bg-[#12151C] rounded-2xl border-2 border-slate-300 dark:border-obsidianBorder font-mono text-indigo-400" id="formula-modal-calc">
                    Calculation formula here
                </div>
            </div>
            <button onclick="closeFormulaModal()" class="w-full bg-indigo-600 hover:bg-indigo-500 text-white font-bold py-2.5 rounded-xl text-xs obsidian-key">Got it</button>
        </div>
    </div>

    <!-- FROZEN TOP NAVIGATION HEADER CONTAINER -->
    <div class="sticky top-0 z-40 bg-white/95 dark:bg-obsidianCard/95 backdrop-blur-md border-b-2 border-slate-300 dark:border-obsidianBorder shadow-xl transition-colors duration-300">
        <header class="px-4 py-3 flex justify-between items-center">
            <div class="flex items-center space-x-3">
                <div class="w-10 h-10 rounded-2xl bg-indigo-600 flex items-center justify-center text-white text-lg shadow-lg obsidian-key">
                    <i class="fa-solid fa-vault"></i>
                </div>
                <div>
                    <h1 class="font-black text-base leading-tight">Ibañez Vault</h1>
                    <p class="text-[10px] text-indigo-400 font-bold tracking-wide">POS & Ledger Management</p>
                </div>
            </div>

            <div class="flex items-center gap-2">
                <button onclick="openQuickActionModal()" class="bg-indigo-600 hover:bg-indigo-500 text-white text-xs font-bold px-3.5 py-2 rounded-xl obsidian-key flex items-center gap-1.5 active:scale-95">
                    <i class="fa-solid fa-plus text-xs"></i> Add
                </button>
                <button onclick="toggleTheme()" class="w-9 h-9 bg-slate-100 dark:bg-[#12151C] hover:bg-slate-200 dark:hover:bg-obsidianBorder text-amber-500 border-2 border-slate-300 dark:border-obsidianBorder rounded-xl obsidian-key flex items-center justify-center">
                    <i class="fa-solid fa-sun" id="theme-icon"></i>
                </button>
                <button onclick="logout()" class="w-9 h-9 bg-slate-100 dark:bg-[#12151C] hover:bg-rose-950/40 text-rose-500 border-2 border-slate-300 dark:border-obsidianBorder rounded-xl obsidian-key flex items-center justify-center">
                    <i class="fa-solid fa-right-from-bracket"></i>
                </button>
            </div>
        </header>

        <!-- Navigation Tabs Ribbon -->
        <nav class="flex space-x-2 px-4 py-2 overflow-x-auto no-scrollbar">
            <button onclick="switchTab('dashboard')" id="tab-btn-dashboard" class="nav-btn text-xs font-bold px-4 py-2 rounded-xl whitespace-nowrap obsidian-key bg-indigo-600 text-white">Dashboard</button>
            <button onclick="switchTab('pos')" id="tab-btn-pos" class="nav-btn text-xs font-bold px-4 py-2 rounded-xl whitespace-nowrap obsidian-key bg-slate-200 dark:bg-[#12151C] text-slate-600 dark:text-slate-400">POS</button>
            <button onclick="switchTab('purchaser')" id="tab-btn-purchaser" class="nav-btn text-xs font-bold px-4 py-2 rounded-xl whitespace-nowrap obsidian-key bg-slate-200 dark:bg-[#12151C] text-slate-600 dark:text-slate-400">Purchaser</button>
            <button onclick="switchTab('transactions')" id="tab-btn-transactions" class="nav-btn text-xs font-bold px-4 py-2 rounded-xl whitespace-nowrap obsidian-key bg-slate-200 dark:bg-[#12151C] text-slate-600 dark:text-slate-400">Transactions</button>
            <button onclick="switchTab('inventory')" id="tab-btn-inventory" class="nav-btn text-xs font-bold px-4 py-2 rounded-xl whitespace-nowrap obsidian-key bg-slate-200 dark:bg-[#12151C] text-slate-600 dark:text-slate-400">Inventory</button>
            <button onclick="switchTab('expenses')" id="tab-btn-expenses" class="nav-btn text-xs font-bold px-4 py-2 rounded-xl whitespace-nowrap obsidian-key bg-slate-200 dark:bg-[#12151C] text-slate-600 dark:text-slate-400">Expenses</button>
            <button onclick="switchTab('utang')" id="tab-btn-utang" class="nav-btn text-xs font-bold px-4 py-2 rounded-xl whitespace-nowrap obsidian-key bg-slate-200 dark:bg-[#12151C] text-slate-600 dark:text-slate-400">Utang</button>
            <button onclick="switchTab('breakeven')" id="tab-btn-breakeven" class="nav-btn text-xs font-bold px-4 py-2 rounded-xl whitespace-nowrap obsidian-key bg-slate-200 dark:bg-[#12151C] text-slate-600 dark:text-slate-400">Break-Even</button>
            <button onclick="switchTab('pl')" id="tab-btn-pl" class="nav-btn text-xs font-bold px-4 py-2 rounded-xl whitespace-nowrap obsidian-key bg-slate-200 dark:bg-[#12151C] text-slate-600 dark:text-slate-400"><i class="fa-solid fa-chart-line mr-1"></i> P&L</button>
        </nav>
    </div>

    <!-- MAIN WORKSPACE -->
    <main class="flex-1 max-w-4xl w-full mx-auto p-4 space-y-5">

        <!-- DASHBOARD TAB -->
        <section id="view-dashboard" class="space-y-5">
            <div class="flex justify-between items-start pt-1">
                <div>
                    <h1 id="dash-greeting" class="text-xl font-black tracking-tight">Hi, Administrator</h1>
                    <div class="flex items-center gap-2 mt-1">
                        <span id="dash-role-pill" class="inline-block px-2.5 py-0.5 rounded-md text-[10px] font-black bg-indigo-600/20 text-indigo-400 border border-indigo-500/30">Administrator</span>
                        <span id="live-date-timestamp" class="text-[11px] font-bold text-slate-400 bg-white dark:bg-obsidianCard px-2.5 py-0.5 rounded-md border-2 border-slate-300 dark:border-obsidianBorder">October 20, 2026 | 00:00:00</span>
                    </div>
                </div>
                <div class="text-right">
                    <span class="text-[10px] uppercase font-black text-slate-400 tracking-wider">TODAY</span>
                    <div id="dash-today-sales" class="text-xl font-black text-emerald-400">₱0</div>
                    <span id="dash-today-count" class="text-[11px] text-slate-400 block font-bold">0 sales</span>
                </div>
            </div>

            <div class="grid grid-cols-2 gap-3.5">
                <div class="p-4 bg-white dark:bg-obsidianCard border-2 border-slate-300 dark:border-obsidianBorder rounded-3xl relative space-y-2 obsidian-key">
                    <div class="flex justify-between items-center">
                        <span class="text-[10px] font-black text-slate-400 tracking-wider uppercase">REVENUE</span>
                        <button onclick="showFormulaInfo('revenue')" class="w-8 h-8 rounded-xl bg-emerald-500/10 border border-emerald-500/20 flex items-center justify-center text-emerald-400 hover:scale-105 transition-all">
                            <i class="fa-solid fa-circle-question text-xs"></i>
                        </button>
                    </div>
                    <div id="dash-revenue" class="text-2xl font-black text-emerald-400">₱0</div>
                    <p class="text-[11px] text-slate-400 font-medium">All completed sales</p>
                </div>

                <div class="p-4 bg-white dark:bg-obsidianCard border-2 border-slate-300 dark:border-obsidianBorder rounded-3xl relative space-y-2 obsidian-key">
                    <div class="flex justify-between items-center">
                        <span class="text-[10px] font-black text-slate-400 tracking-wider uppercase">EXPENSES</span>
                        <button onclick="showFormulaInfo('expenses')" class="w-8 h-8 rounded-xl bg-rose-500/10 border border-rose-500/20 flex items-center justify-center text-rose-400 hover:scale-105 transition-all">
                            <i class="fa-solid fa-circle-question text-xs"></i>
                        </button>
                    </div>
                    <div id="dash-expenses" class="text-2xl font-black text-rose-500">₱150</div>
                    <p class="text-[11px] text-slate-400 font-medium">Costs + store purchases</p>
                </div>

                <div class="p-4 bg-white dark:bg-obsidianCard border-2 border-slate-300 dark:border-obsidianBorder rounded-3xl relative space-y-2 obsidian-key">
                    <div class="flex justify-between items-center">
                        <span class="text-[10px] font-black text-slate-400 tracking-wider uppercase">GROSS PROFIT</span>
                        <button onclick="showFormulaInfo('profit')" class="w-8 h-8 rounded-xl bg-indigo-500/10 border border-indigo-500/20 flex items-center justify-center text-indigo-400 hover:scale-105 transition-all">
                            <i class="fa-solid fa-circle-question text-xs"></i>
                        </button>
                    </div>
                    <div class="flex items-baseline gap-1.5">
                        <div id="dash-profit" class="text-2xl font-black text-indigo-400">₱0</div>
                        <span id="dash-profit-pct" class="text-xs font-bold text-emerald-400 bg-emerald-500/10 px-2 py-0.5 rounded-md">(0%)</span>
                    </div>
                    <p class="text-[11px] text-slate-400 font-medium">Sales minus COGS</p>
                </div>

                <div class="p-4 bg-white dark:bg-obsidianCard border-2 border-slate-300 dark:border-obsidianBorder rounded-3xl relative space-y-2 obsidian-key">
                    <div class="flex justify-between items-center">
                        <span id="dash-winloss-label" class="text-[10px] font-black tracking-wider uppercase text-emerald-400">TODAY'S WIN (NET)</span>
                        <button onclick="showFormulaInfo('winloss')" id="dash-winloss-btn" class="w-8 h-8 rounded-xl bg-emerald-500/10 border border-emerald-500/20 flex items-center justify-center text-emerald-400 hover:scale-105 transition-all">
                            <i class="fa-solid fa-circle-question text-xs"></i>
                        </button>
                    </div>
                    <div id="dash-net-winloss" class="text-2xl font-black text-emerald-400">₱0</div>
                    <p class="text-[11px] text-slate-400 font-medium">Gross profit minus expenses</p>
                </div>
            </div>

            <!-- Quick Actions Grid -->
            <div class="space-y-2.5">
                <span class="text-[11px] font-black text-slate-400 tracking-wider uppercase block">QUICK ACTIONS</span>
                <div class="grid grid-cols-4 gap-2.5">
                    <button onclick="switchTab('pos')" class="bg-white dark:bg-obsidianCard border-2 border-slate-300 dark:border-obsidianBorder p-3.5 rounded-2xl text-center space-y-2 obsidian-key group">
                        <div class="w-11 h-11 rounded-2xl bg-indigo-600/20 text-indigo-400 flex items-center justify-center mx-auto group-hover:scale-110 transition-transform">
                            <i class="fa-solid fa-cart-shopping text-sm"></i>
                        </div>
                        <span class="text-[11px] font-bold block">New Sale</span>
                    </button>
                    <button onclick="switchTab('purchaser')" class="bg-white dark:bg-obsidianCard border-2 border-slate-300 dark:border-obsidianBorder p-3.5 rounded-2xl text-center space-y-2 obsidian-key group">
                        <div class="w-11 h-11 rounded-2xl bg-indigo-600/20 text-indigo-400 flex items-center justify-center mx-auto group-hover:scale-110 transition-transform">
                            <i class="fa-solid fa-basket-shopping text-sm"></i>
                        </div>
                        <span class="text-[11px] font-bold block">Shopping</span>
                    </button>
                    <button onclick="switchTab('expenses')" class="bg-white dark:bg-obsidianCard border-2 border-slate-300 dark:border-obsidianBorder p-3.5 rounded-2xl text-center space-y-2 obsidian-key group">
                        <div class="w-11 h-11 rounded-2xl bg-indigo-600/20 text-indigo-400 flex items-center justify-center mx-auto group-hover:scale-110 transition-transform">
                            <i class="fa-solid fa-wallet text-sm"></i>
                        </div>
                        <span class="text-[11px] font-bold block">Expense</span>
                    </button>
                    <button onclick="switchTab('pl')" class="bg-white dark:bg-obsidianCard border-2 border-slate-300 dark:border-obsidianBorder p-3.5 rounded-2xl text-center space-y-2 obsidian-key group">
                        <div class="w-11 h-11 rounded-2xl bg-indigo-600/20 text-indigo-400 flex items-center justify-center mx-auto group-hover:scale-110 transition-transform">
                            <i class="fa-solid fa-chart-line text-sm"></i>
                        </div>
                        <span class="text-[11px] font-bold block">P&L Report</span>
                    </button>
                </div>
            </div>

            <!-- Recent Sales Section -->
            <div class="space-y-2.5">
                <div class="flex justify-between items-center">
                    <span class="text-[11px] font-black text-slate-400 tracking-wider uppercase">RECENT SALES</span>
                    <button onclick="switchTab('transactions')" class="text-xs font-bold text-indigo-400 hover:underline">See all</button>
                </div>
                <div id="dash-recent-list" class="space-y-2.5"></div>
            </div>
        </section>

        <!-- POS TERMINAL TAB -->
        <section id="view-pos" class="hidden space-y-4 relative pb-32">
            <!-- STICKY CONTROL BAR CONTAINER FOR POS -->
            <div class="sticky top-[112px] z-30 bg-slate-100/95 dark:bg-obsidianDark/95 backdrop-blur-md py-2 space-y-2 transition-colors">
                <div class="flex justify-between items-center">
                    <h2 class="text-lg font-black tracking-wide">POS Terminal</h2>
                </div>

                <div class="relative">
                    <i class="fa-solid fa-magnifying-glass absolute left-3.5 top-3.5 text-slate-400 text-xs"></i>
                    <input type="text" id="pos-search" oninput="renderPOSGrid()" placeholder="Search products" class="w-full bg-white dark:bg-obsidianCard border-2 border-slate-300 dark:border-obsidianBorder rounded-2xl pl-9 pr-4 py-3 text-xs placeholder-slate-400 focus:outline-none focus:border-indigo-500 shadow-inner obsidian-key">
                </div>

                <div class="flex space-x-2 overflow-x-auto no-scrollbar py-1">
                    <button onclick="filterPOSCategory('All')" id="pos-cat-All" class="pos-cat-btn px-4 py-1.5 rounded-xl text-xs font-bold bg-indigo-600 text-white whitespace-nowrap obsidian-key">All</button>
                    <button onclick="filterPOSCategory('Dairy')" id="pos-cat-Dairy" class="pos-cat-btn px-4 py-1.5 rounded-xl text-xs font-bold bg-white dark:bg-obsidianCard text-slate-400 border-2 border-slate-300 dark:border-obsidianBorder whitespace-nowrap obsidian-key">Dairy</button>
                    <button onclick="filterPOSCategory('Canned')" id="pos-cat-Canned" class="pos-cat-btn px-4 py-1.5 rounded-xl text-xs font-bold bg-white dark:bg-obsidianCard text-slate-400 border-2 border-slate-300 dark:border-obsidianBorder whitespace-nowrap obsidian-key">Canned</button>
                    <button onclick="filterPOSCategory('Drinks')" id="pos-cat-Drinks" class="pos-cat-btn px-4 py-1.5 rounded-xl text-xs font-bold bg-white dark:bg-obsidianCard text-slate-400 border-2 border-slate-300 dark:border-obsidianBorder whitespace-nowrap obsidian-key">Drinks</button>
                    <button onclick="filterPOSCategory('Grains')" id="pos-cat-Grains" class="pos-cat-btn px-4 py-1.5 rounded-xl text-xs font-bold bg-white dark:bg-obsidianCard text-slate-400 border-2 border-slate-300 dark:border-obsidianBorder whitespace-nowrap obsidian-key">Grains</button>
                    <button onclick="filterPOSCategory('Noodles')" id="pos-cat-Noodles" class="pos-cat-btn px-4 py-1.5 rounded-xl text-xs font-bold bg-white dark:bg-obsidianCard text-slate-400 border-2 border-slate-300 dark:border-obsidianBorder whitespace-nowrap obsidian-key">Noodles</button>
                    <button onclick="filterPOSCategory('Snacks')" id="pos-cat-Snacks" class="pos-cat-btn px-4 py-1.5 rounded-xl text-xs font-bold bg-white dark:bg-obsidianCard text-slate-400 border-2 border-slate-300 dark:border-obsidianBorder whitespace-nowrap obsidian-key">Snacks</button>
                    <button onclick="filterPOSCategory('Beverages')" id="pos-cat-Beverages" class="pos-cat-btn px-4 py-1.5 rounded-xl text-xs font-bold bg-white dark:bg-obsidianCard text-slate-400 border-2 border-slate-300 dark:border-obsidianBorder whitespace-nowrap obsidian-key">Beverages</button>
                    <button onclick="filterPOSCategory('Condiments')" id="pos-cat-Condiments" class="pos-cat-btn px-4 py-1.5 rounded-xl text-xs font-bold bg-white dark:bg-obsidianCard text-slate-400 border-2 border-slate-300 dark:border-obsidianBorder whitespace-nowrap obsidian-key">Condiments</button>
                    <button onclick="filterPOSCategory('Pantry')" id="pos-cat-Pantry" class="pos-cat-btn px-4 py-1.5 rounded-xl text-xs font-bold bg-white dark:bg-obsidianCard text-slate-400 border-2 border-slate-300 dark:border-obsidianBorder whitespace-nowrap obsidian-key">Pantry</button>
                </div>
            </div>

            <div id="pos-products-grid" class="grid grid-cols-2 gap-3 pt-2"></div>

            <div class="bg-white dark:bg-obsidianCard border-2 border-indigo-500/50 rounded-3xl p-5 space-y-4 shadow-2xl relative obsidian-key">
                <div class="flex justify-between items-center pb-2 border-b border-slate-200 dark:border-obsidianBorder">
                    <div class="flex items-center gap-2">
                        <div class="w-7 h-7 rounded-lg bg-indigo-600 text-white flex items-center justify-center text-xs shadow-md">
                            <i class="fa-solid fa-cart-shopping"></i>
                        </div>
                        <h3 class="text-base font-black tracking-wide">Cart Summary</h3>
                    </div>
                    <button onclick="clearCart()" class="text-xs font-black text-rose-500 hover:text-rose-400 px-3 py-1 rounded-xl bg-rose-500/10 border-2 border-rose-500/30 flex items-center gap-1.5 obsidian-key active:scale-95">
                        <i class="fa-solid fa-trash-can text-[11px]"></i> Clear
                    </button>
                </div>

                <div id="pos-cart-list" class="space-y-3 max-h-56 overflow-y-auto pr-1">
                    <p class="text-xs text-slate-400 py-2">No items in cart yet. Click products above to add.</p>
                </div>

                <div class="pt-3 border-t border-slate-200 dark:border-obsidianBorder space-y-2.5 bg-slate-100 dark:bg-[#12151C] p-3.5 rounded-2xl border-2 border-slate-300 dark:border-obsidianBorder">
                    <div class="flex items-center justify-between">
                        <span class="inline-flex items-center gap-1.5 px-3 py-1 rounded-xl bg-indigo-600 text-white font-black text-xs shadow-md obsidian-key">
                            <i class="fa-solid fa-money-bill-wave"></i> Cash Received
                        </span>
                        <div class="relative w-44">
                            <span class="absolute left-3 top-2.5 text-indigo-400 font-black text-sm">₱</span>
                            <input type="number" id="pos-cash-input" oninput="updatePOSCalculations()" placeholder="0.00" class="w-full bg-white dark:bg-obsidianCard border-2 border-indigo-500/50 rounded-xl pl-8 pr-3 py-2 text-right text-base font-black text-emerald-400 focus:outline-none focus:border-indigo-500 shadow-inner">
                        </div>
                    </div>

                    <div class="flex items-center justify-end gap-1.5 pt-1">
                        <span class="text-[10px] font-bold text-slate-400 uppercase tracking-wider mr-1">Quick:</span>
                        <button onclick="setQuickCash('exact')" class="px-2.5 py-1 rounded-lg text-[10px] font-black bg-indigo-600 text-white obsidian-key">Exact</button>
                        <button onclick="setQuickCash(50)" class="px-2.5 py-1 rounded-lg text-[10px] font-black bg-slate-200 dark:bg-obsidianBorder text-slate-300 obsidian-key">₱50</button>
                        <button onclick="setQuickCash(100)" class="px-2.5 py-1 rounded-lg text-[10px] font-black bg-slate-200 dark:bg-obsidianBorder text-slate-300 obsidian-key">₱100</button>
                        <button onclick="setQuickCash(500)" class="px-2.5 py-1 rounded-lg text-[10px] font-black bg-slate-200 dark:bg-obsidianBorder text-slate-300 obsidian-key">₱500</button>
                        <button onclick="setQuickCash(1000)" class="px-2.5 py-1 rounded-lg text-[10px] font-black bg-slate-200 dark:bg-obsidianBorder text-slate-300 obsidian-key">₱1k</button>
                    </div>
                </div>

                <div id="pos-change-row" class="hidden flex justify-between items-center text-xs px-2 pt-1">
                    <span class="text-slate-400 font-bold">Calculated Change:</span>
                    <span class="text-emerald-400 font-black text-base" id="pos-change-val">₱0</span>
                </div>
            </div>

            <!-- FIXED BOTTOM CHECKOUT BAR -->
            <div class="fixed bottom-0 left-0 right-0 z-40 bg-white/95 dark:bg-obsidianCard/95 backdrop-blur-md border-t-2 border-slate-300 dark:border-obsidianBorder p-3 shadow-2xl transition-colors duration-300">
                <div class="max-w-4xl mx-auto space-y-2.5">
                    <input type="text" id="pos-customer-input" placeholder="Customer Name (Optional for Cash, Required for Utang)" class="w-full bg-slate-100 dark:bg-[#12151C] border-2 border-slate-300 dark:border-obsidianBorder rounded-2xl px-4 py-2.5 text-xs placeholder-slate-400 focus:outline-none focus:border-indigo-500 shadow-inner">
                    
                    <div class="flex justify-between items-center">
                        <div>
                            <span class="text-[10px] text-slate-400 font-bold block uppercase tracking-wider">Total:</span>
                            <div id="pos-total-display" class="text-2xl font-black text-emerald-400">₱0</div>
                        </div>
                        <div class="flex gap-2">
                            <button onclick="checkout('Paid')" class="bg-emerald-500 hover:bg-emerald-400 text-slate-950 font-black px-6 py-3 rounded-2xl text-xs obsidian-key active:scale-95 flex items-center gap-1.5 shadow-lg">
                                <i class="fa-solid fa-money-bill-check"></i> Pay Cash
                            </button>
                            <button onclick="checkout('Utang')" class="bg-amber-500 hover:bg-amber-400 text-slate-950 font-black px-6 py-3 rounded-2xl text-xs obsidian-key active:scale-95 flex items-center gap-1.5 shadow-lg">
                                <i class="fa-solid fa-hand-holding-dollar"></i> Utang
                            </button>
                        </div>
                    </div>
                </div>
            </div>
        </section>

        <!-- STORE PURCHASER TAB -->
        <section id="view-purchaser" class="hidden space-y-4">
            <div class="grid grid-cols-2 gap-3.5">
                <div class="p-4 bg-white dark:bg-obsidianCard border-2 border-slate-300 dark:border-obsidianBorder rounded-3xl space-y-1 obsidian-key">
                    <span class="text-[10px] font-black text-slate-400 uppercase tracking-wider">RUNNING TOTAL</span>
                    <div id="p-running-total" class="text-2xl font-black text-emerald-400">₱0</div>
                </div>
                <div class="p-4 bg-white dark:bg-obsidianCard border-2 border-slate-300 dark:border-obsidianBorder rounded-3xl space-y-1 obsidian-key">
                    <span class="text-[10px] font-black text-slate-400 uppercase tracking-wider">PURCHASED / TOTAL</span>
                    <div id="p-ratio" class="text-2xl font-black">0 / 0</div>
                </div>
            </div>

            <div class="bg-white dark:bg-obsidianCard border-2 border-slate-300 dark:border-obsidianBorder rounded-3xl p-5 space-y-4 obsidian-key">
                <h3 class="font-bold text-sm" id="p-form-title">Add Item</h3>
                <input type="hidden" id="p-edit-id">
                <div class="flex bg-slate-100 dark:bg-[#12151C] p-1 rounded-2xl border-2 border-slate-300 dark:border-obsidianBorder">
                    <button onclick="setPurchaserMode('plan')" id="btn-p-plan" class="flex-1 py-2 rounded-xl text-xs font-bold bg-indigo-600 text-white obsidian-key">Plan Item List</button>
                    <button onclick="setPurchaserMode('log')" id="btn-p-log" class="flex-1 py-2 rounded-xl text-xs font-bold text-slate-400">Log Actual Purchase</button>
                </div>
                
                <div class="space-y-3 text-xs">
                    <div>
                        <label class="text-[10px] font-bold text-slate-400 uppercase tracking-wider block mb-1">ITEM NAME / DESCRIPTION</label>
                        <input type="text" id="p-item-name" placeholder="e.g. Itlog, Shampoo, Colgate" class="w-full bg-slate-100 dark:bg-[#12151C] border-2 border-slate-300 dark:border-obsidianBorder rounded-2xl px-4 py-3">
                    </div>

                    <div id="p-log-details" class="space-y-3">
                        <div class="grid grid-cols-2 gap-3">
                            <div>
                                <label class="text-[10px] font-bold text-slate-400 uppercase tracking-wider block mb-1">TOTAL COST (₱)</label>
                                <input type="number" id="p-cost" value="150" class="w-full bg-slate-100 dark:bg-[#12151C] border-2 border-slate-300 dark:border-obsidianBorder rounded-xl px-3 py-2 font-bold">
                            </div>
                            <div>
                                <label class="text-[10px] font-bold text-slate-400 uppercase tracking-wider block mb-1">QUANTITY</label>
                                <input type="number" id="p-qty" value="1" class="w-full bg-slate-100 dark:bg-[#12151C] border-2 border-slate-300 dark:border-obsidianBorder rounded-xl px-3 py-2 font-bold">
                            </div>
                        </div>
                        <div class="grid grid-cols-2 gap-3">
                            <div>
                                <label class="text-[10px] font-bold text-slate-400 uppercase tracking-wider block mb-1">UNIT METRIC</label>
                                <select id="p-unit" class="w-full bg-slate-100 dark:bg-[#12151C] border-2 border-slate-300 dark:border-obsidianBorder rounded-xl px-3 py-2 font-bold">
                                    <option value="pcs">pcs</option>
                                    <option value="box">box</option>
                                    <option value="kg">kg</option>
                                    <option value="sacks">sacks</option>
                                    <option value="tray">tray</option>
                                    <option value="sachet">sachet</option>
                                </select>
                            </div>
                            <div>
                                <label class="text-[10px] font-bold text-slate-400 uppercase tracking-wider block mb-1">MARGIN (%)</label>
                                <input type="number" id="p-margin" value="20" class="w-full bg-slate-100 dark:bg-[#12151C] border-2 border-slate-300 dark:border-obsidianBorder rounded-xl px-3 py-2 font-bold">
                            </div>
                        </div>
                    </div>

                    <div class="flex gap-2">
                        <button onclick="cancelPurchaserEdit()" id="p-cancel-btn" class="hidden flex-1 bg-slate-200 dark:bg-obsidianBorder font-bold py-3.5 rounded-2xl text-xs obsidian-key">Cancel</button>
                        <button onclick="addPurchaserItem()" id="p-submit-btn" class="flex-1 bg-indigo-600 hover:bg-indigo-500 text-white font-bold py-3.5 rounded-2xl text-xs obsidian-key flex items-center justify-center gap-2">
                            <i class="fa-solid fa-clipboard-list"></i> Add to Planned List
                        </button>
                    </div>
                </div>
            </div>

            <div class="bg-white dark:bg-obsidianCard border-2 border-slate-300 dark:border-obsidianBorder rounded-3xl p-5 space-y-4 obsidian-key">
                <h3 class="font-bold text-sm">Shopping List & Log</h3>
                <div class="flex gap-2">
                    <button onclick="filterPurchaser('All')" id="p-filter-All" class="px-4 py-1.5 rounded-xl text-xs font-bold bg-indigo-600 text-white obsidian-key">All (0)</button>
                    <button onclick="filterPurchaser('To buy')" id="p-filter-Tobuy" class="px-4 py-1.5 rounded-xl text-xs font-bold bg-slate-100 dark:bg-[#12151C] text-slate-400 border-2 border-slate-300 dark:border-obsidianBorder obsidian-key">To buy (0)</button>
                    <button onclick="filterPurchaser('Bought')" id="p-filter-Bought" class="px-4 py-1.5 rounded-xl text-xs font-bold bg-slate-100 dark:bg-[#12151C] text-slate-400 border-2 border-slate-300 dark:border-obsidianBorder obsidian-key">Bought (0)</button>
                </div>
                <div id="purchaser-items-list" class="space-y-2.5 text-xs py-2"></div>
            </div>
        </section>

        <!-- TRANSACTIONS TAB -->
        <section id="view-transactions" class="hidden space-y-4">
            <div class="bg-white dark:bg-obsidianCard border-2 border-slate-300 dark:border-obsidianBorder rounded-3xl p-5 space-y-4 obsidian-key">
                <h2 class="font-bold text-base flex items-center gap-2">
                    <i class="fa-solid fa-receipt text-indigo-400"></i> Transactions Log
                </h2>

                <div class="p-4 bg-gradient-to-r from-indigo-950/40 to-purple-950/40 border-2 border-indigo-500/40 rounded-2xl flex justify-between items-center shadow-inner">
                    <div>
                        <span id="tx-summary-label" class="text-[10px] font-black uppercase tracking-wider text-indigo-400">FILTERED TOTAL AMOUNT</span>
                        <p class="text-[11px] text-slate-400" id="tx-summary-count">0 matching records</p>
                    </div>
                    <div id="tx-summary-val" class="text-2xl font-black text-emerald-400">₱0</div>
                </div>

                <div class="grid grid-cols-2 gap-3 bg-slate-100 dark:bg-[#12151C] p-3 rounded-2xl border-2 border-slate-300 dark:border-obsidianBorder">
                    <div>
                        <label class="text-[10px] font-bold text-slate-400 uppercase tracking-wider block mb-1">From Date</label>
                        <input type="date" id="tx-date-from" onchange="renderTransactions()" class="w-full bg-white dark:bg-obsidianCard border-2 border-slate-300 dark:border-obsidianBorder rounded-xl px-3 py-2 text-xs font-bold focus:outline-none focus:border-indigo-500">
                    </div>
                    <div>
                        <label class="text-[10px] font-bold text-slate-400 uppercase tracking-wider block mb-1">To Date</label>
                        <input type="date" id="tx-date-to" onchange="renderTransactions()" class="w-full bg-white dark:bg-obsidianCard border-2 border-slate-300 dark:border-obsidianBorder rounded-xl px-3 py-2 text-xs font-bold focus:outline-none focus:border-indigo-500">
                    </div>
                </div>

                <div class="relative">
                    <i class="fa-solid fa-magnifying-glass absolute left-3.5 top-3.5 text-slate-400 text-xs"></i>
                    <input type="text" id="tx-search" oninput="renderTransactions()" placeholder="Search name, item or expense" class="w-full bg-slate-100 dark:bg-[#12151C] border-2 border-slate-300 dark:border-obsidianBorder rounded-2xl pl-9 pr-4 py-3 text-xs placeholder-slate-400 focus:outline-none focus:border-indigo-500">
                </div>

                <div class="flex gap-2 overflow-x-auto no-scrollbar">
                    <button onclick="filterTransactions('All')" id="tx-filter-All" class="px-4 py-1.5 rounded-xl text-xs font-bold bg-indigo-600 text-white whitespace-nowrap obsidian-key">All</button>
                    <button onclick="filterTransactions('Sales')" id="tx-filter-Sales" class="px-4 py-1.5 rounded-xl text-xs font-bold bg-slate-100 dark:bg-[#12151C] text-slate-400 border-2 border-slate-300 dark:border-obsidianBorder whitespace-nowrap obsidian-key">Sales</button>
                    <button onclick="filterTransactions('Utang')" id="tx-filter-Utang" class="px-4 py-1.5 rounded-xl text-xs font-bold bg-slate-100 dark:bg-[#12151C] text-slate-400 border-2 border-slate-300 dark:border-obsidianBorder whitespace-nowrap obsidian-key">Utang</button>
                    <button onclick="filterTransactions('Expenses')" id="tx-filter-Expenses" class="px-4 py-1.5 rounded-xl text-xs font-bold bg-slate-100 dark:bg-[#12151C] text-slate-400 border-2 border-slate-300 dark:border-obsidianBorder whitespace-nowrap obsidian-key">Expenses</button>
                </div>

                <div id="full-transactions-list" class="space-y-3 pt-2"></div>
            </div>
        </section>

        <!-- INVENTORY TAB -->
        <section id="view-inventory" class="hidden space-y-4">
            <!-- EXPIRATION WARNING BANNER -->
            <div id="inventory-alert-banner" class="hidden p-4 bg-amber-500/10 border-2 border-amber-500/40 rounded-3xl flex items-center justify-between obsidian-key">
                <div class="flex items-center gap-3">
                    <div class="w-10 h-10 rounded-2xl bg-amber-500 text-slate-950 flex items-center justify-center font-black text-lg shadow-md">
                        <i class="fa-solid fa-triangle-exclamation"></i>
                    </div>
                    <div>
                        <h4 class="font-black text-amber-400 text-xs uppercase tracking-wider">Expiration Warning Alert</h4>
                        <p class="text-xs text-slate-300" id="inventory-alert-text">You have items that are near expiry or already expired.</p>
                    </div>
                </div>
                <button onclick="filterInventory('expired_soon')" class="bg-amber-500 hover:bg-amber-400 text-slate-950 font-black px-3.5 py-2 rounded-xl text-[11px] obsidian-key shadow-lg">View Alerts</button>
            </div>

            <div class="bg-white dark:bg-obsidianCard border-2 border-slate-300 dark:border-obsidianBorder rounded-3xl p-5 space-y-4 obsidian-key">
                <div class="relative">
                    <i class="fa-solid fa-magnifying-glass absolute left-3.5 top-3.5 text-slate-400 text-xs"></i>
                    <input type="text" id="inv-search" oninput="renderInventory()" placeholder="Search products" class="w-full bg-slate-100 dark:bg-[#12151C] border-2 border-slate-300 dark:border-obsidianBorder rounded-2xl pl-9 pr-4 py-3 text-xs placeholder-slate-400 focus:outline-none focus:border-indigo-500">
                </div>

                <!-- ITEM CATEGORY SELECTOR FOR EASY FINDING -->
                <div class="space-y-1.5">
                    <span class="text-[10px] font-black text-slate-400 uppercase tracking-wider">Item Category</span>
                    <div class="flex space-x-2 overflow-x-auto no-scrollbar py-1">
                        <button onclick="filterInventoryCategory('All')" id="inv-cat-All" class="inv-cat-btn px-3.5 py-1.5 rounded-xl text-xs font-bold bg-indigo-600 text-white whitespace-nowrap obsidian-key">All</button>
                        <button onclick="filterInventoryCategory('Dairy')" id="inv-cat-Dairy" class="inv-cat-btn px-3.5 py-1.5 rounded-xl text-xs font-bold bg-slate-100 dark:bg-[#12151C] text-slate-400 border-2 border-slate-300 dark:border-obsidianBorder whitespace-nowrap obsidian-key">Dairy</button>
                        <button onclick="filterInventoryCategory('Canned')" id="inv-cat-Canned" class="inv-cat-btn px-3.5 py-1.5 rounded-xl text-xs font-bold bg-slate-100 dark:bg-[#12151C] text-slate-400 border-2 border-slate-300 dark:border-obsidianBorder whitespace-nowrap obsidian-key">Canned</button>
                        <button onclick="filterInventoryCategory('Drinks')" id="inv-cat-Drinks" class="inv-cat-btn px-3.5 py-1.5 rounded-xl text-xs font-bold bg-slate-100 dark:bg-[#12151C] text-slate-400 border-2 border-slate-300 dark:border-obsidianBorder whitespace-nowrap obsidian-key">Drinks</button>
                        <button onclick="filterInventoryCategory('Grains')" id="inv-cat-Grains" class="inv-cat-btn px-3.5 py-1.5 rounded-xl text-xs font-bold bg-slate-100 dark:bg-[#12151C] text-slate-400 border-2 border-slate-300 dark:border-obsidianBorder whitespace-nowrap obsidian-key">Grains</button>
                        <button onclick="filterInventoryCategory('Noodles')" id="inv-cat-Noodles" class="inv-cat-btn px-3.5 py-1.5 rounded-xl text-xs font-bold bg-slate-100 dark:bg-[#12151C] text-slate-400 border-2 border-slate-300 dark:border-obsidianBorder whitespace-nowrap obsidian-key">Noodles</button>
                        <button onclick="filterInventoryCategory('Snacks')" id="inv-cat-Snacks" class="inv-cat-btn px-3.5 py-1.5 rounded-xl text-xs font-bold bg-slate-100 dark:bg-[#12151C] text-slate-400 border-2 border-slate-300 dark:border-obsidianBorder whitespace-nowrap obsidian-key">Snacks</button>
                        <button onclick="filterInventoryCategory('Beverages')" id="inv-cat-Beverages" class="inv-cat-btn px-3.5 py-1.5 rounded-xl text-xs font-bold bg-slate-100 dark:bg-[#12151C] text-slate-400 border-2 border-slate-300 dark:border-obsidianBorder whitespace-nowrap obsidian-key">Beverages</button>
                        <button onclick="filterInventoryCategory('Condiments')" id="inv-cat-Condiments" class="inv-cat-btn px-3.5 py-1.5 rounded-xl text-xs font-bold bg-slate-100 dark:bg-[#12151C] text-slate-400 border-2 border-slate-300 dark:border-obsidianBorder whitespace-nowrap obsidian-key">Condiments</button>
                        <button onclick="filterInventoryCategory('Pantry')" id="inv-cat-Pantry" class="inv-cat-btn px-3.5 py-1.5 rounded-xl text-xs font-bold bg-slate-100 dark:bg-[#12151C] text-slate-400 border-2 border-slate-300 dark:border-obsidianBorder whitespace-nowrap obsidian-key">Pantry</button>
                    </div>
                </div>
                
                <div class="flex flex-wrap justify-between items-center gap-2 pt-1">
                    <div class="flex gap-2 overflow-x-auto no-scrollbar">
                        <button onclick="filterInventory('All')" id="inv-filter-All" class="px-3.5 py-1.5 rounded-xl text-xs font-bold bg-indigo-600 text-white obsidian-key">All Status</button>
                        <button onclick="filterInventory('Low')" id="inv-filter-Low" class="px-3.5 py-1.5 rounded-xl text-xs font-bold bg-slate-100 dark:bg-[#12151C] text-slate-400 border-2 border-slate-300 dark:border-obsidianBorder obsidian-key">Low stock</button>
                        <button onclick="filterInventory('expired_soon')" id="inv-filter-expired_soon" class="px-3.5 py-1.5 rounded-xl text-xs font-bold bg-slate-100 dark:bg-[#12151C] text-slate-400 border-2 border-slate-300 dark:border-obsidianBorder obsidian-key text-amber-400">⚠️ Expiry Alerts</button>
                    </div>
                    <div class="text-right">
                        <span class="text-[10px] text-slate-400 font-bold block uppercase">Stock value (at cost)</span>
                        <span class="text-lg font-black" id="inv-stock-value">₱0</span>
                    </div>
                </div>

                <div class="grid grid-cols-2 gap-2 pt-1">
                    <button onclick="openRiceCalcModal()" class="bg-amber-500/10 text-amber-400 border border-amber-500/30 p-2.5 rounded-xl font-bold text-xs flex items-center justify-center gap-2 obsidian-key">
                        <i class="fa-solid fa-wheat-awn"></i> Rice Reseller Calc
                    </button>
                    <button onclick="openBulkCalcModal()" class="bg-indigo-500/10 text-indigo-400 border border-indigo-500/30 p-2.5 rounded-xl font-bold text-xs flex items-center justify-center gap-2 obsidian-key">
                        <i class="fa-solid fa-boxes-packing"></i> Bulk Box Calc
                    </button>
                </div>

                <div id="inventory-list" class="space-y-3 pt-1"></div>
                <button id="add-prod-btn" onclick="openAddProductModal()" class="w-full bg-indigo-600 hover:bg-indigo-500 text-white font-bold py-3.5 rounded-2xl text-xs obsidian-key flex items-center justify-center gap-2 shadow-lg">
                    <i class="fa-solid fa-plus"></i> Add Product
                </button>
            </div>
        </section>

        <!-- EXPENSES TAB -->
        <section id="view-expenses" class="hidden space-y-4">
            <div class="p-5 bg-white dark:bg-obsidianCard border-2 border-slate-300 dark:border-obsidianBorder rounded-3xl space-y-1 obsidian-key">
                <span class="text-[10px] font-black text-slate-400 uppercase tracking-wider">TOTAL EXPENSES</span>
                <div id="total-expenses-display" class="text-3xl font-black text-rose-500">₱0</div>
            </div>
            <div id="expenses-empty-state" class="bg-white dark:bg-obsidianCard border-2 border-slate-300 dark:border-obsidianBorder rounded-3xl p-8 text-center space-y-4 hidden obsidian-key">
                <div class="w-16 h-16 rounded-2xl bg-slate-100 dark:bg-slate-800 flex items-center justify-center mx-auto text-slate-400 text-2xl">
                    <i class="fa-solid fa-wallet"></i>
                </div>
                <div>
                    <h3 class="font-bold text-base">No expenses yet</h3>
                    <p class="text-xs text-slate-400 mt-1">Record rent, electricity, salaries and more.</p>
                </div>
            </div>
            <div id="expenses-list-container" class="space-y-2.5"></div>
            <button id="add-exp-btn" onclick="openAddExpenseModal()" class="w-full bg-indigo-600 hover:bg-indigo-500 text-white font-bold py-3.5 rounded-2xl text-xs obsidian-key flex items-center justify-center gap-2 shadow-lg">
                <i class="fa-solid fa-plus"></i> Add Expense
            </button>
        </section>

        <!-- UTANG TAB -->
        <section id="view-utang" class="hidden space-y-4">
            <div class="p-5 bg-white dark:bg-obsidianCard border-2 border-slate-300 dark:border-obsidianBorder rounded-3xl space-y-1 obsidian-key">
                <span class="text-[10px] font-black text-slate-400 uppercase tracking-wider">TOTAL UNCOLLECTED</span>
                <div id="total-utang-display" class="text-3xl font-black text-amber-400">₱0</div>
            </div>
            <div class="relative">
                <i class="fa-solid fa-magnifying-glass absolute left-3.5 top-3.5 text-slate-400 text-xs"></i>
                <input type="text" id="utang-search" oninput="renderUtang()" placeholder="Search customer" class="w-full bg-white dark:bg-obsidianCard border-2 border-slate-300 dark:border-obsidianBorder rounded-2xl pl-9 pr-4 py-3 text-xs placeholder-slate-400 focus:outline-none focus:border-indigo-500 shadow-inner">
            </div>
            <div class="flex gap-2">
                <button onclick="filterUtang('balance')" id="utang-filter-bal" class="px-4 py-1.5 rounded-xl text-xs font-bold bg-indigo-600 text-white obsidian-key">With balance</button>
                <button onclick="filterUtang('all')" id="utang-filter-all" class="px-4 py-1.5 rounded-xl text-xs font-bold bg-white dark:bg-obsidianCard text-slate-400 border-2 border-slate-300 dark:border-obsidianBorder obsidian-key">All customers</button>
            </div>
            <div id="utang-list-container" class="space-y-3"></div>
        </section>

        <!-- BREAK-EVEN CALC TAB -->
        <section id="view-breakeven" class="hidden space-y-4">
            <div class="bg-white dark:bg-obsidianCard border-2 border-slate-300 dark:border-obsidianBorder rounded-3xl p-5 space-y-4 obsidian-key">
                <div>
                    <h2 class="font-bold text-base flex items-center gap-2">
                        <i class="fa-solid fa-scale-balanced text-indigo-400"></i> Store Break-Even & Profit Margin Calculator
                    </h2>
                    <p class="text-xs text-slate-400 mt-1">Calculate how much revenue your store must make to cover fixed overhead costs.</p>
                </div>

                <div class="bg-indigo-950/20 border-2 border-indigo-500/40 rounded-2xl p-4 space-y-3 obsidian-key">
                    <h3 class="text-xs font-bold text-indigo-400 uppercase tracking-wider"><i class="fa-solid fa-calculator mr-1"></i> Gross Profit Margin Formula Builder</h3>
                    <div class="grid grid-cols-2 gap-3">
                        <div>
                            <label class="text-slate-400 text-[10px] font-bold block mb-1 uppercase">Sample Selling Price (₱)</label>
                            <input type="number" id="bm-sell" value="100" oninput="calcMarginFormula()" class="w-full bg-white dark:bg-[#12151C] border-2 border-slate-300 dark:border-obsidianBorder rounded-xl px-3.5 py-2 text-xs font-bold">
                        </div>
                        <div>
                            <label class="text-slate-400 text-[10px] font-bold block mb-1 uppercase">Sample Item Cost (₱)</label>
                            <input type="number" id="bm-cost" value="80" oninput="calcMarginFormula()" class="w-full bg-white dark:bg-[#12151C] border-2 border-slate-300 dark:border-obsidianBorder rounded-xl px-3.5 py-2 text-xs font-bold">
                        </div>
                    </div>
                    <div class="flex justify-between items-center bg-slate-900/60 p-3 rounded-xl border-2 border-indigo-500/30">
                        <div>
                            <span class="text-[10px] text-slate-400 block font-bold">Formula: (Selling Price - Cost) ÷ Selling Price × 100%</span>
                            <span class="text-xs text-indigo-300 font-mono" id="bm-formula-txt">(100 - 80) ÷ 100 × 100%</span>
                        </div>
                        <div class="text-right">
                            <span class="text-[10px] text-slate-400 uppercase font-bold block">Calculated Margin</span>
                            <span class="text-lg font-black text-emerald-400" id="bm-margin-val">20%</span>
                        </div>
                    </div>
                </div>

                <div class="bg-slate-100 dark:bg-[#12151C] border-2 border-slate-300 dark:border-obsidianBorder rounded-2xl p-4 space-y-3 obsidian-key">
                    <h3 class="text-xs font-bold text-indigo-400 uppercase tracking-wider"><i class="fa-solid fa-file-invoice-dollar mr-1"></i> Monthly Fixed Overhead Costs</h3>
                    <div class="space-y-2.5 text-xs">
                        <div>
                            <label class="block mb-1 font-bold">Store Rent (₱)</label>
                            <input type="number" id="be-rent" value="11000" oninput="calcBreakEven()" class="w-full bg-white dark:bg-obsidianCard border-2 border-slate-300 dark:border-obsidianBorder rounded-xl px-3.5 py-2 font-bold">
                        </div>
                        <div>
                            <label class="block mb-1 font-bold">Staff / Helper Salary (₱)</label>
                            <input type="number" id="be-salary" value="15000" oninput="calcBreakEven()" class="w-full bg-white dark:bg-obsidianCard border-2 border-slate-300 dark:border-obsidianBorder rounded-xl px-3.5 py-2 font-bold">
                        </div>
                        <div>
                            <label class="block mb-1 font-bold">Electricity / Meralco (₱)</label>
                            <input type="number" id="be-electricity" value="5000" oninput="calcBreakEven()" class="w-full bg-white dark:bg-obsidianCard border-2 border-slate-300 dark:border-obsidianBorder rounded-xl px-3.5 py-2 font-bold">
                        </div>
                        <div>
                            <label class="block mb-1 font-bold">Water Bill (₱)</label>
                            <input type="number" id="be-water" value="600" oninput="calcBreakEven()" class="w-full bg-white dark:bg-obsidianCard border-2 border-slate-300 dark:border-obsidianBorder rounded-xl px-3.5 py-2 font-bold">
                        </div>
                        <div>
                            <label class="block mb-1 font-bold">Barangay Permits & Taxes (₱)</label>
                            <input type="number" id="be-permits" value="1000" oninput="calcBreakEven()" class="w-full bg-white dark:bg-obsidianCard border-2 border-slate-300 dark:border-obsidianBorder rounded-xl px-3.5 py-2 font-bold">
                        </div>
                        <div>
                            <label class="block mb-1 font-bold">Delivery / Transpo Fare (₱)</label>
                            <input type="number" id="be-delivery" value="0" oninput="calcBreakEven()" class="w-full bg-white dark:bg-obsidianCard border-2 border-slate-300 dark:border-obsidianBorder rounded-xl px-3.5 py-2 font-bold">
                        </div>
                        <div>
                            <label class="block mb-1 font-bold text-emerald-400">Target Gross Margin % (Used for Break-Even)</label>
                            <input type="number" id="be-margin-pct" value="20" oninput="calcBreakEven()" class="w-full bg-white dark:bg-obsidianCard border-2 border-slate-300 dark:border-obsidianBorder rounded-xl px-3.5 py-2 font-bold text-emerald-400">
                        </div>
                    </div>
                </div>

                <div class="bg-slate-100 dark:bg-[#12151C] border-2 border-slate-300 dark:border-obsidianBorder rounded-2xl p-5 space-y-4 obsidian-key">
                    <div>
                        <span class="text-[10px] text-slate-400 uppercase font-black tracking-wider">TOTAL MONTHLY FIXED OVERHEAD</span>
                        <div id="be-out-total" class="text-2xl font-black mt-0.5">₱32,600.00</div>
                    </div>
                    <div class="pt-3 border-t border-slate-300 dark:border-obsidianBorder">
                        <span class="text-[10px] text-slate-400 uppercase font-black tracking-wider">MONTHLY BREAK-EVEN SALES</span>
                        <div id="be-out-monthly" class="text-2xl font-black text-amber-400 mt-0.5">₱163,000.00</div>
                    </div>
                    <div class="pt-3 border-t border-slate-300 dark:border-obsidianBorder">
                        <span class="text-[10px] text-slate-400 uppercase font-black tracking-wider">DAILY TARGET SALES (30 DAYS)</span>
                        <div id="be-out-daily" class="text-2xl font-black text-emerald-400 mt-0.5">₱5,433.33 / day</div>
                    </div>
                </div>
            </div>
        </section>

        <!-- P&L / WIN-LOSS REPORT TAB -->
        <section id="view-pl" class="hidden space-y-4">
            <div class="bg-white dark:bg-obsidianCard border-2 border-slate-300 dark:border-obsidianBorder rounded-3xl p-5 space-y-4 obsidian-key">
                <div>
                    <h2 class="font-bold text-base flex items-center gap-2">
                        <i class="fa-solid fa-chart-line text-indigo-400"></i> Profit & Loss (P&L) Win-Loss Summary
                    </h2>
                    <p class="text-xs text-slate-400 mt-1">Daily and monthly store wins (net earnings) or losses.</p>
                </div>

                <div class="grid grid-cols-2 gap-3.5">
                    <div class="p-4 bg-slate-100 dark:bg-[#12151C] border-2 border-slate-300 dark:border-obsidianBorder rounded-2xl space-y-1 obsidian-key">
                        <span class="text-[10px] font-black text-slate-400 uppercase tracking-wider">MONTHLY GROSS PROFIT</span>
                        <div id="pl-monthly-profit" class="text-xl font-black text-emerald-400">₱0</div>
                    </div>
                    <div class="p-4 bg-slate-100 dark:bg-[#12151C] border-2 border-slate-300 dark:border-obsidianBorder rounded-2xl space-y-1 obsidian-key">
                        <span class="text-[10px] font-black text-slate-400 uppercase tracking-wider">MONTHLY NET WIN / LOSS</span>
                        <div id="pl-monthly-net" class="text-xl font-black text-indigo-400">₱0</div>
                    </div>
                </div>

                <!-- OVERHEAD BREAK-EVEN MONETIZATION COMPARISON CARD -->
                <div class="p-4 bg-slate-100 dark:bg-[#12151C] border-2 border-amber-500/40 rounded-2xl space-y-3 obsidian-key">
                    <div class="flex justify-between items-center">
                        <div>
                            <span class="text-[10px] font-black text-amber-400 uppercase tracking-wider block"><i class="fa-solid fa-bullseye mr-1"></i> OVERHEAD BREAK-EVEN GAP</span>
                            <span class="text-xs font-bold text-slate-400">(Monthly Fixed Overhead − Monthly Gross Profit)</span>
                        </div>
                        <span id="pl-overhead-pct" class="text-xs font-black px-2.5 py-1 rounded-lg bg-amber-500/10 text-amber-400 border border-amber-500/20">0% Covered</span>
                    </div>

                    <div class="flex justify-between items-baseline">
                        <div id="pl-overhead-remaining" class="text-2xl font-black text-rose-500">₱32,600.00 Needed</div>
                        <span id="pl-overhead-target-lbl" class="text-[11px] font-bold text-slate-400">Target: =monthly overhead cost (₱32,600)</span>
                    </div>

                    <div class="w-full bg-slate-200 dark:bg-obsidianBorder h-2.5 rounded-full overflow-hidden">
                        <div id="pl-overhead-progress-bar" class="bg-amber-400 h-full rounded-full transition-all duration-500" style="width: 0%"></div>
                    </div>
                    <p class="text-[11px] text-slate-400 italic" id="pl-overhead-status-msg">Earn gross profit to pay off fixed bills (Rent, Meralco, Salary).</p>
                </div>

                <div class="space-y-3 pt-2">
                    <h3 class="font-bold text-xs uppercase tracking-wider"><i class="fa-solid fa-calendar-day mr-1"></i> Daily Win / Loss Records</h3>
                    <div id="pl-daily-list" class="space-y-2.5 text-xs"></div>
                </div>
            </div>
        </section>

    </main>

    <!-- QUICK ACTIONS MODAL -->
    <div id="quick-action-modal" class="fixed inset-0 z-50 bg-black/80 backdrop-blur-sm hidden flex items-end sm:items-center justify-center p-0 sm:p-4">
        <div class="bg-white dark:bg-obsidianCard border-t-2 sm:border-2 border-slate-300 dark:border-obsidianBorder rounded-t-3xl sm:rounded-3xl w-full max-w-md p-5 space-y-3 shadow-2xl max-h-[85vh] overflow-y-auto obsidian-key">
            <div class="flex justify-between items-center pb-2 border-b border-slate-200 dark:border-obsidianBorder">
                <h3 class="font-black text-xl">Vault Quick Actions</h3>
                <button onclick="closeQuickActionModal()" class="w-8 h-8 bg-slate-100 dark:bg-obsidianBorder rounded-xl flex items-center justify-center text-slate-400 hover:text-white obsidian-key">
                    <i class="fa-solid fa-xmark text-sm"></i>
                </button>
            </div>
            <div class="space-y-2 text-xs">
                <button onclick="switchTab('pos'); closeQuickActionModal();" class="w-full bg-slate-100 dark:bg-[#12151C] p-3.5 rounded-2xl border-2 border-slate-300 dark:border-obsidianBorder flex items-center justify-between text-left obsidian-key group">
                    <div class="flex items-center gap-3.5">
                        <div class="w-10 h-10 rounded-xl bg-indigo-600/20 text-indigo-400 flex items-center justify-center text-sm"><i class="fa-solid fa-cart-shopping"></i></div>
                        <div><span class="font-bold text-sm block">New Sale</span><span class="text-[11px] text-slate-400">Open POS terminal</span></div>
                    </div>
                    <i class="fa-solid fa-chevron-right text-slate-400"></i>
                </button>

                <button onclick="openQuickSellModal(); closeQuickActionModal();" class="w-full bg-slate-100 dark:bg-[#12151C] p-3.5 rounded-2xl border-2 border-slate-300 dark:border-obsidianBorder flex items-center justify-between text-left obsidian-key group">
                    <div class="flex items-center gap-3.5">
                        <div class="w-10 h-10 rounded-xl bg-indigo-600/20 text-indigo-400 flex items-center justify-center text-sm"><i class="fa-solid fa-scale-unbalanced"></i></div>
                        <div><span class="font-bold text-sm block">Quick Sell by Kilo</span><span class="text-[11px] text-slate-400">Sell rice or sugar by kg or ₱</span></div>
                    </div>
                    <i class="fa-solid fa-chevron-right text-slate-400"></i>
                </button>

                <button onclick="openRiceCalcModal(); closeQuickActionModal();" class="w-full bg-slate-100 dark:bg-[#12151C] p-3.5 rounded-2xl border-2 border-slate-300 dark:border-obsidianBorder flex items-center justify-between text-left obsidian-key group">
                    <div class="flex items-center gap-3.5">
                        <div class="w-10 h-10 rounded-xl bg-amber-500/20 text-amber-400 flex items-center justify-center text-sm"><i class="fa-solid fa-wheat-awn"></i></div>
                        <div><span class="font-bold text-sm block">Rice Reseller Pricing Calculator</span><span class="text-[11px] text-slate-400">Calculate sack costs, loss & margin per kg</span></div>
                    </div>
                    <i class="fa-solid fa-chevron-right text-slate-400"></i>
                </button>

                <button onclick="openBulkCalcModal(); closeQuickActionModal();" class="w-full bg-slate-100 dark:bg-[#12151C] p-3.5 rounded-2xl border-2 border-slate-300 dark:border-obsidianBorder flex items-center justify-between text-left obsidian-key group">
                    <div class="flex items-center gap-3.5">
                        <div class="w-10 h-10 rounded-xl bg-indigo-500/20 text-indigo-400 flex items-center justify-center text-sm"><i class="fa-solid fa-boxes-packing"></i></div>
                        <div><span class="font-bold text-sm block">Bulk Case / Box Pricing Calculator</span><span class="text-[11px] text-slate-400">Compute box freight & unit selling price</span></div>
                    </div>
                    <i class="fa-solid fa-chevron-right text-slate-400"></i>
                </button>

                <button onclick="openAddProductModal(); closeQuickActionModal();" class="w-full bg-slate-100 dark:bg-[#12151C] p-3.5 rounded-2xl border-2 border-slate-300 dark:border-obsidianBorder flex items-center justify-between text-left obsidian-key group">
                    <div class="flex items-center gap-3.5">
                        <div class="w-10 h-10 rounded-xl bg-indigo-600/20 text-indigo-400 flex items-center justify-center text-sm"><i class="fa-solid fa-tag"></i></div>
                        <div><span class="font-bold text-sm block">Add Product</span><span class="text-[11px] text-slate-400">New item in inventory</span></div>
                    </div>
                    <i class="fa-solid fa-chevron-right text-slate-400"></i>
                </button>

                <button onclick="openAddExpenseModal(); closeQuickActionModal();" class="w-full bg-slate-100 dark:bg-[#12151C] p-3.5 rounded-2xl border-2 border-slate-300 dark:border-obsidianBorder flex items-center justify-between text-left obsidian-key group">
                    <div class="flex items-center gap-3.5">
                        <div class="w-10 h-10 rounded-xl bg-indigo-600/20 text-indigo-400 flex items-center justify-center text-sm"><i class="fa-solid fa-wallet"></i></div>
                        <div><span class="font-bold text-sm block">Add Expense</span><span class="text-[11px] text-slate-400">Rent, bills, salary...</span></div>
                    </div>
                    <i class="fa-solid fa-chevron-right text-slate-400"></i>
                </button>
            </div>
        </div>
    </div>

    <!-- EDIT TRANSACTION MODAL -->
    <div id="edit-tx-modal" class="fixed inset-0 z-50 bg-black/80 backdrop-blur-sm hidden flex items-center justify-center p-4">
        <div class="bg-white dark:bg-obsidianCard border-2 border-slate-300 dark:border-obsidianBorder rounded-3xl w-full max-w-md p-5 space-y-4 shadow-2xl obsidian-key">
            <div class="flex justify-between items-center pb-2 border-b border-slate-200 dark:border-obsidianBorder">
                <h3 class="font-bold text-base">Edit Transaction</h3>
                <button onclick="closeEditTxModal()" class="text-slate-400 hover:text-white"><i class="fa-solid fa-xmark text-base"></i></button>
            </div>
            <div class="space-y-3 text-xs">
                <input type="hidden" id="etx-id">
                <div>
                    <label class="block mb-1 font-bold">Date & Time</label>
                    <input type="text" id="etx-date" class="w-full bg-slate-100 dark:bg-[#12151C] border-2 border-slate-300 dark:border-obsidianBorder rounded-xl px-3.5 py-2.5">
                </div>
                <div>
                    <label class="block mb-1 font-bold">Customer Name / Note</label>
                    <input type="text" id="etx-customer" class="w-full bg-slate-100 dark:bg-[#12151C] border-2 border-slate-300 dark:border-obsidianBorder rounded-xl px-3.5 py-2.5">
                </div>
                <div>
                    <label class="block mb-1 font-bold">Item Description</label>
                    <input type="text" id="etx-items" class="w-full bg-slate-100 dark:bg-[#12151C] border-2 border-slate-300 dark:border-obsidianBorder rounded-xl px-3.5 py-2.5">
                </div>
                <div class="grid grid-cols-3 gap-2">
                    <div>
                        <label class="block mb-1 font-bold">Total (₱)</label>
                        <input type="number" id="etx-amount" class="w-full bg-slate-100 dark:bg-[#12151C] border-2 border-slate-300 dark:border-obsidianBorder rounded-xl px-2.5 py-2.5 font-bold">
                    </div>
                    <div>
                        <label class="block mb-1 font-bold">Cash (₱)</label>
                        <input type="number" id="etx-cash" class="w-full bg-slate-100 dark:bg-[#12151C] border-2 border-slate-300 dark:border-obsidianBorder rounded-xl px-2.5 py-2.5 font-bold">
                    </div>
                    <div>
                        <label class="block mb-1 font-bold">Change (₱)</label>
                        <input type="number" id="etx-change" class="w-full bg-slate-100 dark:bg-[#12151C] border-2 border-slate-300 dark:border-obsidianBorder rounded-xl px-2.5 py-2.5 font-bold">
                    </div>
                </div>
                <div>
                    <label class="block mb-1 font-bold">Status / Type</label>
                    <select id="etx-type" class="w-full bg-slate-100 dark:bg-[#12151C] border-2 border-slate-300 dark:border-obsidianBorder rounded-xl px-3.5 py-2.5 font-bold">
                        <option value="Paid">Paid</option>
                        <option value="Utang">Utang</option>
                        <option value="Expense">Expense</option>
                    </select>
                </div>
            </div>
            <div class="flex gap-2 pt-2">
                <button onclick="closeEditTxModal()" class="flex-1 bg-slate-200 dark:bg-obsidianBorder font-bold py-3 rounded-xl text-xs obsidian-key">Cancel</button>
                <button onclick="saveTxEdit()" class="flex-1 bg-indigo-600 hover:bg-indigo-500 text-white font-bold py-3 rounded-xl text-xs obsidian-key shadow-lg">Save Changes</button>
            </div>
        </div>
    </div>

    <!-- QUICK SELL MODAL -->
    <div id="quicksell-modal" class="fixed inset-0 z-50 bg-black/80 backdrop-blur-sm hidden flex items-center justify-center p-4">
        <div class="bg-white dark:bg-obsidianCard border-2 border-slate-300 dark:border-obsidianBorder rounded-3xl w-full max-w-md p-5 space-y-4 shadow-2xl obsidian-key">
            <div class="flex justify-between items-center pb-1">
                <h3 class="font-bold text-lg">Quick Sell by Kilo</h3>
                <button onclick="closeQuickSellModal()" class="w-8 h-8 bg-slate-100 dark:bg-obsidianBorder rounded-xl flex items-center justify-center text-slate-400 hover:text-white obsidian-key"><i class="fa-solid fa-xmark text-sm"></i></button>
            </div>

            <div class="flex items-center gap-2">
                <select id="qs-product-select" onchange="onQsProductChange()" class="flex-1 bg-slate-100 dark:bg-[#12151C] border-2 border-indigo-500/40 rounded-xl px-3 py-2 text-xs font-extrabold text-indigo-400 focus:outline-none">
                </select>
            </div>

            <div class="flex bg-slate-100 dark:bg-[#12151C] p-1 rounded-2xl border-2 border-slate-300 dark:border-obsidianBorder">
                <button onclick="setQsMode('kilo')" id="qs-btn-kilo" class="flex-1 py-2 rounded-xl text-xs font-bold bg-indigo-600 text-white obsidian-key">By kilo</button>
                <button onclick="setQsMode('amount')" id="qs-btn-amount" class="flex-1 py-2 rounded-xl text-xs font-bold text-slate-400 obsidian-key">By amount (₱)</button>
            </div>

            <div class="space-y-3 text-xs">
                <div>
                    <label id="qs-input-label" class="text-[10px] font-bold text-slate-400 uppercase tracking-wider block mb-1">KILOS</label>
                    <input type="number" id="qs-value-input" oninput="updateQuickSell()" placeholder="e.g. 0.5, 1, 2.5" class="w-full bg-slate-100 dark:bg-[#12151C] border-2 border-slate-300 dark:border-obsidianBorder rounded-2xl px-4 py-3 text-sm font-bold focus:outline-none focus:border-indigo-500">
                    <p class="text-[10px] text-slate-400 mt-1" id="qs-stock-display">Stock: 0</p>
                </div>

                <div>
                    <label class="text-[10px] font-bold text-slate-400 uppercase tracking-wider block mb-1">CUSTOMER NAME</label>
                    <input type="text" id="qs-customer" placeholder="Walk-in Customer" class="w-full bg-slate-100 dark:bg-[#12151C] border-2 border-slate-300 dark:border-obsidianBorder rounded-2xl px-4 py-3">
                </div>

                <div class="flex justify-between items-center p-3.5 bg-slate-100 dark:bg-[#12151C] border-2 border-slate-300 dark:border-obsidianBorder rounded-2xl">
                    <span class="text-slate-400 font-bold" id="qs-formula">0 kg × ₱0</span>
                    <span class="text-emerald-400 font-black text-lg" id="qs-total">₱0</span>
                </div>

                <div class="flex gap-2 pt-2">
                    <button onclick="executeQuickSell('Paid')" class="flex-1 bg-emerald-500 hover:bg-emerald-400 text-slate-950 font-black py-3.5 rounded-2xl text-xs obsidian-key active:scale-95 shadow-lg">Pay Cash</button>
                    <button onclick="executeQuickSell('Utang')" class="flex-1 bg-amber-500 hover:bg-amber-400 text-slate-950 font-black py-3.5 rounded-2xl text-xs obsidian-key active:scale-95 shadow-lg">Utang</button>
                </div>
            </div>
        </div>
    </div>

    <!-- ADD / EDIT PRODUCT MODAL -->
    <div id="add-product-modal" class="fixed inset-0 z-50 bg-black/80 backdrop-blur-sm hidden flex items-center justify-center p-4">
        <div class="bg-white dark:bg-obsidianCard border-2 border-slate-300 dark:border-obsidianBorder rounded-3xl w-full max-w-md p-5 space-y-4 shadow-2xl obsidian-key">
            <div class="flex justify-between items-center pb-2 border-b border-slate-200 dark:border-obsidianBorder">
                <h3 class="font-bold text-base" id="ap-title">Add Product</h3>
                <button onclick="closeAddProductModal()" class="text-slate-400 hover:text-white"><i class="fa-solid fa-xmark text-base"></i></button>
            </div>
            <div class="space-y-3 text-xs">
                <input type="hidden" id="ap-id">
                <div>
                    <label class="block mb-1 font-bold">Product Name</label>
                    <input type="text" id="ap-name" placeholder="e.g. Silver Swan Vinegar" class="w-full bg-slate-100 dark:bg-[#12151C] border-2 border-slate-300 dark:border-obsidianBorder rounded-xl px-3 py-2">
                </div>
                <div>
                    <label class="block mb-1 font-bold">Category</label>
                    <input type="text" id="ap-cat" placeholder="e.g. Condiments, Pantry, Dairy" class="w-full bg-slate-100 dark:bg-[#12151C] border-2 border-slate-300 dark:border-obsidianBorder rounded-xl px-3 py-2">
                </div>
                <div class="grid grid-cols-2 gap-3">
                    <div>
                        <label class="block mb-1 font-bold">Cost (₱)</label>
                        <input type="number" id="ap-cost" value="10" class="w-full bg-slate-100 dark:bg-[#12151C] border-2 border-slate-300 dark:border-obsidianBorder rounded-xl px-3 py-2">
                    </div>
                    <div>
                        <label class="block mb-1 font-bold">Margin (₱)</label>
                        <input type="number" id="ap-margin" value="3" class="w-full bg-slate-100 dark:bg-[#12151C] border-2 border-slate-300 dark:border-obsidianBorder rounded-xl px-3 py-2">
                    </div>
                </div>
                <div class="grid grid-cols-2 gap-3">
                    <div>
                        <label class="block mb-1 font-bold">Stock Qty</label>
                        <input type="number" id="ap-stock" value="10" class="w-full bg-slate-100 dark:bg-[#12151C] border-2 border-slate-300 dark:border-obsidianBorder rounded-xl px-3 py-2">
                    </div>
                    <div>
                        <label class="block mb-1 font-bold">Unit Metric</label>
                        <input type="text" id="ap-unit" value="pcs" class="w-full bg-slate-100 dark:bg-[#12151C] border-2 border-slate-300 dark:border-obsidianBorder rounded-xl px-3 py-2">
                    </div>
                </div>
                <div class="grid grid-cols-2 gap-3">
                    <div>
                        <label class="block mb-1 font-bold">Date Added</label>
                        <input type="date" id="ap-date-added" class="w-full bg-slate-100 dark:bg-[#12151C] border-2 border-slate-300 dark:border-obsidianBorder rounded-xl px-3 py-2 font-bold">
                    </div>
                    <div>
                        <label class="block mb-1 font-bold text-amber-400">Expiration Date (Optional)</label>
                        <input type="date" id="ap-expiry" class="w-full bg-slate-100 dark:bg-[#12151C] border-2 border-slate-300 dark:border-obsidianBorder rounded-xl px-3 py-2 font-bold text-amber-400">
                    </div>
                </div>
            </div>
            <div class="flex gap-2 pt-2">
                <button onclick="closeAddProductModal()" class="flex-1 bg-slate-200 dark:bg-obsidianBorder font-bold py-2.5 rounded-xl text-xs obsidian-key">Cancel</button>
                <button onclick="saveProduct()" class="flex-1 bg-indigo-600 hover:bg-indigo-500 text-white font-bold py-2.5 rounded-xl text-xs obsidian-key shadow-lg">Save Product</button>
            </div>
        </div>
    </div>

    <!-- ADD / EDIT EXPENSE MODAL -->
    <div id="add-expense-modal" class="fixed inset-0 z-50 bg-black/80 backdrop-blur-sm hidden flex items-center justify-center p-4">
        <div class="bg-white dark:bg-obsidianCard border-2 border-slate-300 dark:border-obsidianBorder rounded-3xl w-full max-w-md p-5 space-y-4 shadow-2xl obsidian-key">
            <div class="flex justify-between items-center pb-2 border-b border-slate-200 dark:border-obsidianBorder">
                <h3 class="font-bold text-base" id="ae-title">Record Expense</h3>
                <button onclick="closeAddExpenseModal()" class="text-slate-400 hover:text-white"><i class="fa-solid fa-xmark text-base"></i></button>
            </div>
            <div class="space-y-3 text-xs">
                <input type="hidden" id="ae-id">
                <div>
                    <label class="block mb-1 font-bold">Description</label>
                    <input type="text" id="ae-desc" placeholder="e.g. Electric Bill" class="w-full bg-slate-100 dark:bg-[#12151C] border-2 border-slate-300 dark:border-obsidianBorder rounded-xl px-3 py-2">
                </div>
                <div>
                    <label class="block mb-1 font-bold">Amount (₱)</label>
                    <input type="number" id="ae-amount" placeholder="0.00" class="w-full bg-slate-100 dark:bg-[#12151C] border-2 border-slate-300 dark:border-obsidianBorder rounded-xl px-3 py-2">
                </div>
            </div>
            <div class="flex gap-2 pt-2">
                <button onclick="closeAddExpenseModal()" class="flex-1 bg-slate-200 dark:bg-obsidianBorder font-bold py-2.5 rounded-xl text-xs obsidian-key">Cancel</button>
                <button onclick="saveExpense()" class="flex-1 bg-indigo-600 hover:bg-indigo-500 text-white font-bold py-2.5 rounded-xl text-xs obsidian-key shadow-lg">Save Expense</button>
            </div>
        </div>
    </div>

    <!-- SETTLEMENT MODAL FOR UTANG -->
    <div id="settle-utang-modal" class="fixed inset-0 z-50 bg-black/80 backdrop-blur-sm hidden flex items-center justify-center p-4">
        <div class="bg-white dark:bg-obsidianCard border-2 border-slate-300 dark:border-obsidianBorder rounded-3xl w-full max-w-sm p-5 space-y-4 shadow-2xl obsidian-key">
            <div class="flex justify-between items-center pb-2 border-b border-slate-200 dark:border-obsidianBorder">
                <h3 class="font-bold text-base">Settle Utang Balance</h3>
                <button onclick="closeSettleModal()" class="text-slate-400 hover:text-white"><i class="fa-solid fa-xmark text-base"></i></button>
            </div>
            <div class="space-y-3 text-xs">
                <input type="hidden" id="su-customer">
                <div>
                    <label class="block mb-1 font-bold text-slate-400">Customer</label>
                    <div id="su-customer-name" class="font-black text-sm text-indigo-400">Customer</div>
                </div>
                <div>
                    <label class="block mb-1 font-bold text-slate-400">Total Outstanding Balance</label>
                    <div id="su-balance-display" class="font-black text-lg text-amber-400">₱0</div>
                </div>
                <div>
                    <label class="block mb-1 font-bold">Payment Amount Collected (₱)</label>
                    <input type="number" id="su-payment" placeholder="0.00" class="w-full bg-slate-100 dark:bg-[#12151C] border-2 border-slate-300 dark:border-obsidianBorder rounded-xl px-3.5 py-2.5 text-base font-black text-emerald-400">
                </div>
            </div>
            <div class="flex gap-2 pt-2">
                <button onclick="closeSettleModal()" class="flex-1 bg-slate-200 dark:bg-obsidianBorder font-bold py-3 rounded-xl text-xs obsidian-key">Cancel</button>
                <button onclick="confirmSettleUtang()" class="flex-1 bg-emerald-500 hover:bg-emerald-400 text-slate-950 font-black py-3 rounded-xl text-xs obsidian-key shadow-lg">Confirm Payment</button>
            </div>
        </div>
    </div>

    <script>
        let currentRole = 'Admin';
        const PASSWORDS = { 'Admin': '12345bert', 'Store Keeper': 'store123' };

        let products = [
            { id: '1', name: 'Bear Brand 33g', category: 'Dairy', cost: 10, margin: 3, price: 13, stock: 10, unit: 'sachet', dateAdded: '2026-09-01', expiryDate: '2027-05-15' },
            { id: '2', name: 'Century Tuna 155g', category: 'Canned', cost: 30, margin: 8, price: 38, stock: 18, unit: 'can', dateAdded: '2026-09-05', expiryDate: '2028-01-10' },
            { id: '3', name: 'Coca-Cola 1.5L Bottle', category: 'Drinks', cost: 60, margin: 12, price: 72, stock: 24, unit: 'bottle', dateAdded: '2026-10-01', expiryDate: '2026-11-05' },
            { id: '4', name: 'Coco Pandan Rice', category: 'Grains', cost: 1050, margin: 300, price: 1350, stock: 6, unit: 'pcs', dateAdded: '2026-09-10', expiryDate: '' },
            { id: '5', name: 'Jasmine Rice', category: 'Grains', cost: 48, margin: 12, price: 60, stock: 47, unit: 'kg', dateAdded: '2026-09-15', expiryDate: '' },
            { id: '6', name: 'Kopiko Brown Coffee', category: 'Drinks', cost: 7, margin: 3, price: 10, stock: 57, unit: 'sachet', dateAdded: '2026-09-20', expiryDate: '2027-08-20' },
            { id: '7', name: 'Lucky Me Instant Noodles', category: 'Noodles', cost: 10, margin: 3, price: 13, stock: 40, unit: 'pack', dateAdded: '2026-09-25', expiryDate: '2026-10-25' },
            { id: '8', name: 'Piattos Cheese 85g', category: 'Snacks', cost: 30, margin: 8, price: 38, stock: 25, unit: 'pack', dateAdded: '2026-10-02', expiryDate: '2026-11-12' },
            { id: '9', name: 'Red Bull Energy Drink', category: 'Beverages', cost: 45, margin: 10, price: 55, stock: 15, unit: 'can', dateAdded: '2026-10-05', expiryDate: '2026-10-18' },
            { id: '10', name: 'Silver Swan Vinegar 200ml', category: 'Condiments', cost: 12, margin: 3, price: 15, stock: 20, unit: 'pouch', dateAdded: '2026-10-08', expiryDate: '2027-12-01' },
            { id: '11', name: 'Datu Puti Patis 350ml', category: 'Condiments', cost: 22, margin: 5, price: 27, stock: 15, unit: 'bottle', dateAdded: '2026-10-10', expiryDate: '2028-02-15' },
            { id: '12', name: 'Special Tuyo 100g', category: 'Pantry', cost: 35, margin: 10, price: 45, stock: 12, unit: 'pack', dateAdded: '2026-10-12', expiryDate: '2027-01-30' }
        ];

        let cart = {};
        let purchaserItems = [
            { id: 'p1', name: 'Itlog', status: 'To buy', amount: 0, qty: 0, unit: 'tray', margin: 20 },
            { id: 'p2', name: 'Shampoo', status: 'Bought', amount: 150, qty: 10, unit: 'sachet', margin: 25 }
        ];
        let expenses = [
            { id: 'e1', description: 'Vegetables', amount: 150, date: '2026-10-20' }
        ];
        let purchaserMode = 'plan';
        let currentPurchaserFilter = 'All';
        let currentTxFilter = 'All';
        let currentPosCategory = 'All';
        let currentInvCategory = 'All';
        let currentInvFilter = 'All';
        let qsMode = 'kilo';
        let selectedQsProductId = '5';
        let utangFilter = 'balance';

        let transactions = [
            { id: 'TX-1309', date: '2026-10-19 14:20:00', customer: 'Mina', items: 'Coca-Cola 1.5L Bottle x1, Jasmine Rice x1, Kopiko Brown Coffee x1', amount: 142, cogs: 115, cash: 500, change: 358, type: 'Paid' },
            { id: 'TX-1001', date: '2026-10-20 09:15:00', customer: 'Dikong', items: 'Jasmine Rice (20 kg) x1, Bear Brand 33g x21', amount: 1473, cogs: 1170, cash: 2000, change: 527, type: 'Paid' },
            { id: 'TX-8813', date: '2026-10-20 11:45:00', customer: 'Fing', items: 'Bear Brand 33g x1, Century Tuna 155g x1, Coca-Cola 1.5L Bottle x1', amount: 123, cogs: 100, cash: 123, change: 0, type: 'Utang' },
            { id: 'e1', date: '2026-10-20 12:00:00', customer: 'Store Expense', items: 'Vegetables', amount: 150, cogs: 0, cash: 150, change: 0, type: 'Expense' }
        ];

        function updateLiveDateTime() {
            const now = new Date();
            const options = { year: 'numeric', month: 'long', day: '2-digit' };
            const dateStr = now.toLocaleDateString('en-US', options);
            const timeStr = now.toTimeString().split(' ')[0];
            const el = document.getElementById('live-date-timestamp');
            if (el) el.textContent = `${dateStr} | ${timeStr}`;
        }
        setInterval(updateLiveDateTime, 1000);

        function togglePasswordVisibility() {
            let passInput = document.getElementById('login-pass');
            let icon = document.getElementById('pass-toggle-icon');
            if (passInput.type === 'password') {
                passInput.type = 'text';
                icon.className = 'fa-solid fa-eye-slash';
            } else {
                passInput.type = 'password';
                icon.className = 'fa-solid fa-eye';
            }
        }

        function performLogin() {
            let role = document.getElementById('login-role').value;
            let pass = document.getElementById('login-pass').value;
            let err = document.getElementById('login-error');

            if (pass === PASSWORDS[role]) {
                currentRole = role;
                document.getElementById('login-modal').classList.add('hidden');
                err.classList.add('hidden');
                document.getElementById('login-pass').value = '';
                applyUserRolePermissions();
                showToast(`Logged in as ${role}`);
            } else {
                err.classList.remove('hidden');
            }
        }

        function logout() {
            document.getElementById('login-modal').classList.remove('hidden');
        }

        function applyUserRolePermissions() {
            let greeting = document.getElementById('dash-greeting');
            let pill = document.getElementById('dash-role-pill');
            
            if (currentRole === 'Store Keeper') {
                greeting.textContent = 'Hi, Store Keeper';
                pill.textContent = 'Store Keeper';
            } else {
                greeting.textContent = 'Hi, Administrator';
                pill.textContent = 'Administrator';
            }

            renderTransactions();
            renderInventory();
            renderExpenses();
            renderPurchaser();
            renderDashboard();
            renderUtang();
            renderPLReport();
        }

        function toggleTheme() {
            let root = document.getElementById('html-root');
            let icon = document.getElementById('theme-icon');
            if (root.classList.contains('dark')) {
                root.classList.remove('dark');
                icon.className = "fa-solid fa-moon";
                showToast("Day mode activated");
            } else {
                root.classList.add('dark');
                icon.className = "fa-solid fa-sun";
                showToast("Night mode activated");
            }
        }

        function switchTab(tab) {
            ['dashboard', 'pos', 'purchaser', 'transactions', 'inventory', 'expenses', 'utang', 'breakeven', 'pl'].forEach(t => {
                const view = document.getElementById('view-' + t);
                const btn = document.getElementById('tab-btn-' + t);
                if (view) view.classList.add('hidden');
                if (btn) btn.className = "nav-btn text-xs font-bold px-4 py-2 rounded-xl whitespace-nowrap obsidian-key bg-slate-200 dark:bg-[#12151C] text-slate-600 dark:text-slate-400";
            });
            const activeView = document.getElementById('view-' + tab);
            const activeBtn = document.getElementById('tab-btn-' + tab);
            if (activeView) activeView.classList.remove('hidden');
            if (activeBtn) activeBtn.className = "nav-btn text-xs font-bold px-4 py-2 rounded-xl whitespace-nowrap obsidian-key bg-indigo-600 text-white";
            
            if (tab === 'pl') renderPLReport();
            if (tab === 'dashboard') renderDashboard();
            if (tab === 'utang') renderUtang();
            if (tab === 'inventory') renderInventory();
        }

        function openQuickActionModal() { document.getElementById('quick-action-modal').classList.remove('hidden'); }
        function closeQuickActionModal() { document.getElementById('quick-action-modal').classList.add('hidden'); }

        /* RICE RESELLER PRICING CALCULATOR LOGIC */
        function openRiceCalcModal() {
            document.getElementById('rice-calc-modal').classList.remove('hidden');
            calcRiceFormula();
        }
        function closeRiceCalcModal() { document.getElementById('rice-calc-modal').classList.add('hidden'); }

        function calcRiceFormula() {
            let sackCost = parseFloat(document.getElementById('rc-sack-cost').value) || 0;
            let weight = parseFloat(document.getElementById('rc-weight').value) || 50;
            let spill = parseFloat(document.getElementById('rc-spill').value) || 0;
            let transport = parseFloat(document.getElementById('rc-transport').value) || 0;
            let packaging = parseFloat(document.getElementById('rc-packaging').value) || 0;
            let margin = parseFloat(document.getElementById('rc-margin').value) || 20;

            let netWeight = Math.max(0.1, weight - spill);
            let totalCapital = sackCost + transport + (netWeight * packaging);
            let actualCostPerKg = totalCapital / netWeight;
            let recSellingPrice = actualCostPerKg * (1 + (margin / 100));

            document.getElementById('rc-out-netweight').textContent = netWeight.toFixed(1) + ' KG';
            document.getElementById('rc-out-capital').textContent = '₱' + totalCapital.toFixed(2);
            document.getElementById('rc-out-actualcost').textContent = '₱' + actualCostPerKg.toFixed(2);
            document.getElementById('rc-out-recprice').textContent = '₱' + recSellingPrice.toFixed(2);
        }

        function importRiceToInventory() {
            let name = document.getElementById('rc-name').value.trim() || 'JASMINE SPECIAL';
            let sackCost = parseFloat(document.getElementById('rc-sack-cost').value) || 0;
            let weight = parseFloat(document.getElementById('rc-weight').value) || 50;
            let spill = parseFloat(document.getElementById('rc-spill').value) || 0;
            let transport = parseFloat(document.getElementById('rc-transport').value) || 0;
            let packaging = parseFloat(document.getElementById('rc-packaging').value) || 0;
            let margin = parseFloat(document.getElementById('rc-margin').value) || 20;

            let netWeight = Math.max(0.1, weight - spill);
            let totalCapital = sackCost + transport + (netWeight * packaging);
            let actualCostPerKg = totalCapital / netWeight;
            let recPricePerKg = actualCostPerKg * (1 + (margin / 100));
            let todayStr = new Date().toISOString().split('T')[0];

            let opt = document.getElementById('rc-import-opt').value;

            if (opt === 'both' || opt === 'kg') {
                products.push({
                    id: Date.now().toString(),
                    name: name + ' (Per KG)',
                    category: 'Grains',
                    cost: Math.round(actualCostPerKg),
                    margin: Math.round(recPricePerKg - actualCostPerKg),
                    price: Math.round(recPricePerKg),
                    stock: netWeight,
                    unit: 'kg',
                    dateAdded: todayStr,
                    expiryDate: ''
                });
            }

            if (opt === 'both' || opt === 'sack') {
                products.push({
                    id: (Date.now() + 1).toString(),
                    name: name + ' (Whole Sack)',
                    category: 'Grains',
                    cost: Math.round(totalCapital),
                    margin: Math.round(totalCapital * (margin / 100)),
                    price: Math.round(totalCapital * (1 + (margin / 100))),
                    stock: 1,
                    unit: 'sack',
                    dateAdded: todayStr,
                    expiryDate: ''
                });
            }

            closeRiceCalcModal();
            renderInventory();
            renderPOSGrid();
            showToast("Rice pricing imported to inventory!");
        }

        /* BULK CASE / BOX PRICING CALCULATOR LOGIC */
        function openBulkCalcModal() {
            document.getElementById('bulk-calc-modal').classList.remove('hidden');
            calcBulkFormula();
        }
        function closeBulkCalcModal() { document.getElementById('bulk-calc-modal').classList.add('hidden'); }

        function calcBulkFormula() {
            let boxCost = parseFloat(document.getElementById('bc-box-cost').value) || 0;
            let units = parseFloat(document.getElementById('bc-units').value) || 1;
            let freight = parseFloat(document.getElementById('bc-freight').value) || 0;
            let margin = parseFloat(document.getElementById('bc-margin').value) || 25;

            let totalBoxCost = boxCost + freight;
            let unitCost = totalBoxCost / Math.max(1, units);
            let recSellingPrice = unitCost * (1 + (margin / 100));

            document.getElementById('bc-out-boxcost').textContent = '₱' + totalBoxCost.toFixed(2);
            document.getElementById('bc-out-unitcost').textContent = '₱' + unitCost.toFixed(2);
            document.getElementById('bc-out-recprice').textContent = '₱' + recSellingPrice.toFixed(2);
        }

        function importBulkToInventory() {
            let name = document.getElementById('bc-name').value.trim() || 'Bulk Item';
            let boxCost = parseFloat(document.getElementById('bc-box-cost').value) || 0;
            let units = parseFloat(document.getElementById('bc-units').value) || 1;
            let freight = parseFloat(document.getElementById('bc-freight').value) || 0;
            let margin = parseFloat(document.getElementById('bc-margin').value) || 25;

            let totalBoxCost = boxCost + freight;
            let unitCost = totalBoxCost / Math.max(1, units);
            let recSellingPrice = unitCost * (1 + (margin / 100));
            let todayStr = new Date().toISOString().split('T')[0];

            products.push({
                id: Date.now().toString(),
                name: name,
                category: 'General',
                cost: Math.round(unitCost),
                margin: Math.round(recSellingPrice - unitCost),
                price: Math.round(recSellingPrice),
                stock: units,
                unit: 'pcs',
                dateAdded: todayStr,
                expiryDate: ''
            });

            closeBulkCalcModal();
            renderInventory();
            renderPOSGrid();
            showToast("Bulk box items imported to inventory!");
        }

        function showFormulaInfo(type) {
            let modal = document.getElementById('formula-modal');
            let title = document.getElementById('formula-modal-title');
            let desc = document.getElementById('formula-modal-desc');
            let calc = document.getElementById('formula-modal-calc');

            if (type === 'revenue') {
                title.innerHTML = '<i class="fa-solid fa-circle-question text-emerald-400"></i> Revenue Formula';
                desc.textContent = "Total Revenue represents all completed sales transactions collected.";
                calc.textContent = "Sum of (Item Selling Price × Quantity Sold)";
            } else if (type === 'expenses') {
                title.innerHTML = '<i class="fa-solid fa-circle-question text-rose-500"></i> Expenses Formula';
                desc.textContent = "Total Expenses include all recorded store bills, operational overheads, and store purchases.";
                calc.textContent = "Sum of All Expenses & Purchaser Logs";
            } else if (type === 'profit') {
                title.innerHTML = '<i class="fa-solid fa-circle-question text-indigo-400"></i> Gross Profit Formula';
                desc.textContent = "Gross Profit is your total sales minus the cost of goods sold (COGS).";
                calc.textContent = "Gross Profit = Sales - COGS\nMargin % = (Gross Profit ÷ Sales) × 100%";
            } else if (type === 'winloss') {
                title.innerHTML = '<i class="fa-solid fa-circle-question text-emerald-400"></i> Today\'s Net Win / Loss';
                desc.textContent = "Net Win calculates your actual daily take-home earnings after paying off today's expenses.";
                calc.textContent = "Net Win/Loss = Gross Profit - Today's Expenses";
            }
            modal.classList.remove('hidden');
        }
        function closeFormulaModal() { document.getElementById('formula-modal').classList.add('hidden'); }

        function setQuickCash(val) {
            let input = document.getElementById('pos-cash-input');
            if (val === 'exact') {
                let total = Object.values(cart).reduce((sum, item) => sum + (item.price * item.qty), 0);
                input.value = total;
            } else {
                input.value = val;
            }
            updatePOSCalculations();
        }

        function openAddProductModal(id = null) {
            if (currentRole !== 'Admin') {
                showToast("Access Denied: Admin authorization required.");
                return;
            }
            let modal = document.getElementById('add-product-modal');
            let title = document.getElementById('ap-title');
            let todayStr = new Date().toISOString().split('T')[0];

            if (id) {
                let p = products.find(prod => prod.id === id);
                if (p) {
                    title.textContent = 'Edit Product';
                    document.getElementById('ap-id').value = p.id;
                    document.getElementById('ap-name').value = p.name;
                    document.getElementById('ap-cat').value = p.category;
                    document.getElementById('ap-cost').value = p.cost;
                    document.getElementById('ap-margin').value = p.margin;
                    document.getElementById('ap-stock').value = p.stock;
                    document.getElementById('ap-unit').value = p.unit;
                    document.getElementById('ap-date-added').value = p.dateAdded || todayStr;
                    document.getElementById('ap-expiry').value = p.expiryDate || '';
                }
            } else {
                title.textContent = 'Add Product';
                document.getElementById('ap-id').value = '';
                document.getElementById('ap-name').value = '';
                document.getElementById('ap-cat').value = 'General';
                document.getElementById('ap-cost').value = 10;
                document.getElementById('ap-margin').value = 3;
                document.getElementById('ap-stock').value = 10;
                document.getElementById('ap-unit').value = 'pcs';
                document.getElementById('ap-date-added').value = todayStr;
                document.getElementById('ap-expiry').value = '';
            }
            modal.classList.remove('hidden');
        }

        function closeAddProductModal() { document.getElementById('add-product-modal').classList.add('hidden'); }

        function deleteProduct(id) {
            if (currentRole !== 'Admin') {
                showToast("Access Denied: Admin authorization required.");
                return;
            }
            if (confirm("Delete this product from inventory?")) {
                products = products.filter(p => p.id !== id);
                renderInventory();
                renderPOSGrid();
                showToast("Product deleted.");
            }
        }

        function openAddExpenseModal(id = null) {
            if (currentRole !== 'Admin') {
                showToast("Access Denied: Admin authorization required.");
                return;
            }
            let modal = document.getElementById('add-expense-modal');
            let title = document.getElementById('ae-title');
            if (id) {
                let e = expenses.find(item => item.id === id);
                if (e) {
                    title.textContent = 'Edit Expense';
                    document.getElementById('ae-id').value = e.id;
                    document.getElementById('ae-desc').value = e.description;
                    document.getElementById('ae-amount').value = e.amount;
                }
            } else {
                title.textContent = 'Record Expense';
                document.getElementById('ae-id').value = '';
                document.getElementById('ae-desc').value = '';
                document.getElementById('ae-amount').value = '';
            }
            modal.classList.remove('hidden');
        }

        function closeAddExpenseModal() { document.getElementById('add-expense-modal').classList.add('hidden'); }

        function saveExpense() {
            if (currentRole !== 'Admin') {
                showToast("Access Denied: Admin authorization required.");
                return;
            }
            let id = document.getElementById('ae-id').value;
            let desc = document.getElementById('ae-desc').value.trim();
            let amount = parseFloat(document.getElementById('ae-amount').value) || 0;
            if (!desc || amount <= 0) return;

            let now = new Date();
            let todayDate = now.toISOString().split('T')[0] + ' ' + now.toTimeString().split(' ')[0];

            if (id) {
                let e = expenses.find(item => item.id === id);
                if (e) { e.description = desc; e.amount = amount; }
            } else {
                let newId = 'e-' + Date.now();
                expenses.push({ id: newId, description: desc, amount, date: todayDate.split(' ')[0] });
                transactions.unshift({
                    id: newId, date: todayDate, customer: 'Store Expense', items: desc, amount: amount, cogs: 0, cash: amount, change: 0, type: 'Expense'
                });
            }

            closeAddExpenseModal();
            renderExpenses();
            renderTransactions();
            renderRecentSales();
            renderDashboard();
            renderPLReport();
            showToast("Expense saved & synced!");
        }

        function deleteExpense(id) {
            if (currentRole !== 'Admin') {
                showToast("Access Denied: Admin authorization required.");
                return;
            }
            if (confirm("Delete this expense?")) {
                expenses = expenses.filter(e => e.id !== id);
                transactions = transactions.filter(t => t.id !== id);
                renderExpenses();
                renderTransactions();
                renderDashboard();
                renderPLReport();
                showToast("Expense deleted.");
            }
        }

        function renderExpenses() {
            let total = expenses.reduce((sum, e) => sum + e.amount, 0);
            document.getElementById('total-expenses-display').textContent = '₱' + total.toLocaleString();
            document.getElementById('dash-expenses').textContent = '₱' + total.toLocaleString();
            let emptyState = document.getElementById('expenses-empty-state');
            let list = document.getElementById('expenses-list-container');

            if (expenses.length === 0) {
                emptyState.classList.remove('hidden');
                list.innerHTML = '';
                return;
            }
            emptyState.classList.add('hidden');
            let html = '';
            expenses.forEach(e => {
                html += `
                    <div class="p-4 bg-white dark:bg-obsidianCard border-2 border-slate-300 dark:border-obsidianBorder rounded-2xl flex justify-between items-center text-xs obsidian-key">
                        <div>
                            <span class="font-bold text-sm">${e.description}</span>
                            <p class="text-[10px] text-slate-400">${e.date}</p>
                            ${currentRole === 'Admin' ? `
                            <div class="flex gap-2 mt-2">
                                <button onclick="openAddExpenseModal('${e.id}')" class="bg-indigo-500/10 text-indigo-400 font-bold px-3 py-1 rounded-xl text-[11px] obsidian-key">Edit</button>
                                <button onclick="deleteExpense('${e.id}')" class="bg-rose-500/10 text-rose-500 font-bold px-3 py-1 rounded-xl text-[11px] obsidian-key">Delete</button>
                            </div>` : ''}
                        </div>
                        <span class="font-black text-rose-500 text-base">₱${e.amount.toLocaleString()}</span>
                    </div>`;
            });
            list.innerHTML = html;
        }

        function setPurchaserMode(mode) {
            purchaserMode = mode;
            let btnPlan = document.getElementById('btn-p-plan');
            let btnLog = document.getElementById('btn-p-log');
            let submitBtn = document.getElementById('p-submit-btn');

            if (mode === 'plan') {
                btnPlan.className = "flex-1 py-2 rounded-xl text-xs font-bold bg-indigo-600 text-white obsidian-key";
                btnLog.className = "flex-1 py-2 rounded-xl text-xs font-bold text-slate-400 obsidian-key";
                submitBtn.innerHTML = '<i class="fa-solid fa-clipboard-list"></i> Add to Planned List';
            } else {
                btnLog.className = "flex-1 py-2 rounded-xl text-xs font-bold bg-indigo-600 text-white obsidian-key";
                btnPlan.className = "flex-1 py-2 rounded-xl text-xs font-bold text-slate-400 obsidian-key";
                submitBtn.innerHTML = '<i class="fa-solid fa-cart-shopping"></i> Add & Save Purchase';
            }
        }

        function addPurchaserItem() {
            let editId = document.getElementById('p-edit-id').value;
            let name = document.getElementById('p-item-name').value.trim();
            if (!name) return;

            if (editId && currentRole !== 'Admin') {
                showToast("Access Denied: Admin authorization required.");
                return;
            }

            let amount = parseFloat(document.getElementById('p-cost').value) || 0;
            let qty = parseFloat(document.getElementById('p-qty').value) || 1;
            let unit = document.getElementById('p-unit').value;
            let margin = parseFloat(document.getElementById('p-margin').value) || 20;
            let status = purchaserMode === 'plan' && !editId ? 'To buy' : 'Bought';

            if (editId) {
                let item = purchaserItems.find(i => i.id === editId);
                if (item) {
                    item.name = name;
                    item.amount = amount;
                    item.qty = qty;
                    item.unit = unit;
                    item.margin = margin;
                }
                cancelPurchaserEdit();
                showToast("Purchaser item updated!");
            } else {
                purchaserItems.push({
                    id: 'p-' + Date.now(), name, status, amount, qty, unit, margin
                });
                showToast("Item added!");
            }

            document.getElementById('p-item-name').value = '';
            renderPurchaser();
        }

        function editPurchaserItem(id) {
            if (currentRole !== 'Admin') {
                showToast("Access Denied: Admin authorization required.");
                return;
            }
            let item = purchaserItems.find(i => i.id === id);
            if (!item) return;

            document.getElementById('p-edit-id').value = item.id;
            document.getElementById('p-item-name').value = item.name;
            document.getElementById('p-cost').value = item.amount;
            document.getElementById('p-qty').value = item.qty;
            document.getElementById('p-unit').value = item.unit;
            document.getElementById('p-margin').value = item.margin;

            document.getElementById('p-form-title').textContent = 'Edit Purchaser Item';
            document.getElementById('p-submit-btn').innerHTML = '<i class="fa-solid fa-check"></i> Save Changes';
            document.getElementById('p-cancel-btn').classList.remove('hidden');
            window.scrollTo({ top: 0, behavior: 'smooth' });
        }

        function cancelPurchaserEdit() {
            document.getElementById('p-edit-id').value = '';
            document.getElementById('p-item-name').value = '';
            document.getElementById('p-cost').value = '150';
            document.getElementById('p-qty').value = '1';
            document.getElementById('p-unit').value = 'pcs';
            document.getElementById('p-margin').value = '20';

            document.getElementById('p-form-title').textContent = 'Add Item';
            document.getElementById('p-submit-btn').innerHTML = '<i class="fa-solid fa-clipboard-list"></i> Add to Planned List';
            document.getElementById('p-cancel-btn').classList.add('hidden');
        }

        function deletePurchaserItem(id) {
            if (currentRole !== 'Admin') {
                showToast("Access Denied: Admin authorization required.");
                return;
            }
            if (confirm("Delete this purchaser item?")) {
                purchaserItems = purchaserItems.filter(i => i.id !== id);
                renderPurchaser();
                showToast("Purchaser item deleted.");
            }
        }

        function importPurchaserToInventory(id) {
            let item = purchaserItems.find(i => i.id === id);
            if (!item) return;

            let unitCost = item.qty > 0 ? (item.amount / item.qty) : item.amount;
            let marginVal = unitCost * (item.margin / 100);
            let sellingPrice = unitCost + marginVal;
            let todayStr = new Date().toISOString().split('T')[0];

            products.push({
                id: Date.now().toString(),
                name: item.name,
                category: 'General',
                cost: Math.round(unitCost),
                margin: Math.round(marginVal),
                price: Math.round(sellingPrice),
                stock: item.qty || 1,
                unit: item.unit || 'pcs',
                dateAdded: todayStr,
                expiryDate: ''
            });

            renderInventory();
            renderPOSGrid();
            showToast(`Imported ${item.name} to inventory!`);
        }

        function filterPurchaser(filter) {
            currentPurchaserFilter = filter;
            ['All', 'Tobuy', 'Bought'].forEach(f => {
                let btn = document.getElementById('p-filter-' + f);
                if (btn) btn.className = (f === filter || (filter === 'To buy' && f === 'Tobuy')) ? "px-4 py-1.5 rounded-xl text-xs font-bold bg-indigo-600 text-white obsidian-key" : "px-4 py-1.5 rounded-xl text-xs font-bold bg-slate-100 dark:bg-[#12151C] text-slate-400 border-2 border-slate-300 dark:border-obsidianBorder obsidian-key";
            });
            renderPurchaser();
        }

        function renderPurchaser() {
            let boughtItems = purchaserItems.filter(i => i.status === 'Bought');
            let total = boughtItems.reduce((sum, i) => sum + i.amount, 0);
            document.getElementById('p-running-total').textContent = '₱' + total.toLocaleString();
            document.getElementById('p-ratio').textContent = `${boughtItems.length} / ${purchaserItems.length}`;

            let filtered = purchaserItems.filter(i => {
                if (currentPurchaserFilter === 'To buy') return i.status === 'To buy';
                if (currentPurchaserFilter === 'Bought') return i.status === 'Bought';
                return true;
            });

            let list = document.getElementById('purchaser-items-list');
            if (filtered.length === 0) {
                list.innerHTML = '<p class="text-xs text-slate-400 py-4 text-center">No items.</p>';
                return;
            }

            let html = '';
            filtered.forEach(i => {
                html += `
                    <div class="p-4 bg-slate-100 dark:bg-[#12151C] border-2 border-slate-300 dark:border-obsidianBorder rounded-2xl space-y-2 text-xs obsidian-key">
                        <div class="flex justify-between items-center">
                            <div>
                                <span class="font-bold text-sm">${i.name}</span>
                                <div class="mt-1 flex items-center gap-2">
                                    <span class="px-2 py-0.5 rounded text-[10px] font-black ${i.status === 'Bought' ? 'bg-emerald-500/20 text-emerald-400' : 'bg-amber-500/20 text-amber-400'}">${i.status}</span>
                                    <span class="text-[10px] text-slate-400">Margin: ${i.margin}%</span>
                                </div>
                            </div>
                            <div class="text-right">
                                <span class="font-black text-emerald-400 text-sm">₱${i.amount.toLocaleString()}</span>
                                <p class="text-[10px] text-slate-400">${i.qty} ${i.unit}</p>
                            </div>
                        </div>
                        <div class="flex justify-end gap-2 pt-2 border-t border-slate-200 dark:border-obsidianBorder/60">
                            ${i.status === 'Bought' ? `<button onclick="importPurchaserToInventory('${i.id}')" class="bg-emerald-500/10 text-emerald-400 font-bold px-3 py-1 rounded-xl text-[11px] obsidian-key"><i class="fa-solid fa-file-import mr-1"></i> Import</button>` : ''}
                            ${currentRole === 'Admin' ? `
                            <button onclick="editPurchaserItem('${i.id}')" class="bg-indigo-500/10 text-indigo-400 font-bold px-3 py-1 rounded-xl text-[11px] obsidian-key">Edit</button>
                            <button onclick="deletePurchaserItem('${i.id}')" class="bg-rose-500/10 text-rose-500 font-bold px-3 py-1 rounded-xl text-[11px] obsidian-key">Delete</button>` : ''}
                        </div>
                    </div>`;
            });
            list.innerHTML = html;
        }

        function saveProduct() {
            if (currentRole !== 'Admin') {
                showToast("Access Denied: Admin authorization required.");
                return;
            }
            let id = document.getElementById('ap-id').value;
            let name = document.getElementById('ap-name').value.trim();
            let category = document.getElementById('ap-cat').value.trim() || 'General';
            let cost = parseFloat(document.getElementById('ap-cost').value) || 0;
            let margin = parseFloat(document.getElementById('ap-margin').value) || 0;
            let stock = parseFloat(document.getElementById('ap-stock').value) || 0;
            let unit = document.getElementById('ap-unit').value.trim() || 'pcs';
            let dateAdded = document.getElementById('ap-date-added').value || new Date().toISOString().split('T')[0];
            let expiryDate = document.getElementById('ap-expiry').value || '';

            if (!name) return;
            let price = cost + margin;

            if (id) {
                let p = products.find(prod => prod.id === id);
                if (p) { p.name = name; p.category = category; p.cost = cost; p.margin = margin; p.price = price; p.stock = stock; p.unit = unit; p.dateAdded = dateAdded; p.expiryDate = expiryDate; }
            } else {
                products.push({ id: Date.now().toString(), name, category, cost, margin, price, stock, unit, dateAdded, expiryDate });
            }

            closeAddProductModal();
            renderInventory();
            renderPOSGrid();
            showToast("Product saved!");
        }

        function getExpiryStatus(expiryStr) {
            if (!expiryStr) return { status: 'none', label: '', badgeClass: '' };
            let today = new Date();
            today.setHours(0,0,0,0);
            let exp = new Date(expiryStr);
            exp.setHours(0,0,0,0);

            let diffDays = Math.ceil((exp - today) / (1000 * 60 * 60 * 24));

            if (diffDays < 0) {
                return { status: 'expired', label: `Expired (${Math.abs(diffDays)}d ago)`, badgeClass: 'bg-rose-500/20 text-rose-400 border border-rose-500/40' };
            } else if (diffDays <= 30) {
                return { status: 'warning', label: `Expiring in ${diffDays}d`, badgeClass: 'bg-amber-500/20 text-amber-400 border border-amber-500/40' };
            } else {
                return { status: 'good', label: `Expires: ${expiryStr}`, badgeClass: 'bg-emerald-500/10 text-emerald-400 border border-emerald-500/20' };
            }
        }

        function filterInventoryCategory(cat) {
            currentInvCategory = cat;
            ['All', 'Dairy', 'Canned', 'Drinks', 'Grains', 'Noodles', 'Snacks', 'Beverages', 'Condiments', 'Pantry'].forEach(c => {
                let btn = document.getElementById('inv-cat-' + c);
                if (btn) btn.className = (c === cat) ? "inv-cat-btn px-3.5 py-1.5 rounded-xl text-xs font-bold bg-indigo-600 text-white whitespace-nowrap obsidian-key" : "inv-cat-btn px-3.5 py-1.5 rounded-xl text-xs font-bold bg-slate-100 dark:bg-[#12151C] text-slate-400 border-2 border-slate-300 dark:border-obsidianBorder whitespace-nowrap obsidian-key";
            });
            renderInventory();
        }

        function renderInventory() {
            let list = document.getElementById('inventory-list');
            let query = (document.getElementById('inv-search')?.value || '').toLowerCase();
            let totalVal = products.reduce((sum, p) => sum + (p.cost * p.stock), 0);
            document.getElementById('inv-stock-value').textContent = '₱' + Math.round(totalVal).toLocaleString();

            let today = new Date();
            today.setHours(0,0,0,0);
            let alertCount = 0;
            products.forEach(p => {
                if (p.expiryDate) {
                    let exp = new Date(p.expiryDate);
                    exp.setHours(0,0,0,0);
                    let diffDays = Math.ceil((exp - today) / (1000 * 60 * 60 * 24));
                    if (diffDays <= 30) alertCount++;
                }
            });

            let banner = document.getElementById('inventory-alert-banner');
            let alertText = document.getElementById('inventory-alert-text');
            if (alertCount > 0) {
                banner.classList.remove('hidden');
                alertText.textContent = `You have ${alertCount} product(s) that are expired or expiring within 30 days.`;
            } else {
                banner.classList.add('hidden');
            }

            let html = '';
            products.forEach(p => {
                if (currentInvCategory !== 'All' && p.category !== currentInvCategory) return;
                if (query && !p.name.toLowerCase().includes(query)) return;
                
                let expInfo = getExpiryStatus(p.expiryDate);
                if (currentInvFilter === 'Low' && p.stock > 5) return;
                if (currentInvFilter === 'expired_soon' && expInfo.status !== 'warning' && expInfo.status !== 'expired') return;

                let cardBorder = 'border-slate-300 dark:border-obsidianBorder';
                if (expInfo.status === 'expired') cardBorder = 'border-rose-500';
                else if (expInfo.status === 'warning') cardBorder = 'border-amber-500';

                html += `
                    <div class="p-4 bg-slate-100 dark:bg-[#12151C] border-2 ${cardBorder} rounded-2xl flex justify-between items-center text-xs obsidian-key">
                        <div class="space-y-1">
                            <h4 class="font-bold text-sm">${p.name}</h4>
                            <p class="text-slate-400">${p.category} • Cost ₱${p.cost}</p>
                            <div class="flex flex-wrap items-center gap-1.5 pt-1">
                                <span class="px-2 py-0.5 rounded text-[10px] font-bold bg-indigo-500/10 text-indigo-400 border border-indigo-500/20">Added: ${p.dateAdded || 'N/A'}</span>
                                ${p.expiryDate ? `<span class="px-2 py-0.5 rounded text-[10px] font-bold ${expInfo.badgeClass}">${expInfo.label}</span>` : ''}
                            </div>
                            ${currentRole === 'Admin' ? `
                            <div class="flex gap-2 pt-2">
                                <button onclick="openAddProductModal('${p.id}')" class="bg-indigo-500/10 text-indigo-400 font-bold px-3 py-1 rounded-xl text-[11px] obsidian-key">Edit</button>
                                <button onclick="deleteProduct('${p.id}')" class="bg-rose-500/10 text-rose-500 font-bold px-3 py-1 rounded-xl text-[11px] obsidian-key">Delete</button>
                            </div>` : ''}
                        </div>
                        <div class="text-right">
                            <div class="font-black text-emerald-400 text-sm">₱${p.price}</div>
                            <span class="text-slate-400 font-medium block mt-1">${p.stock} ${p.unit}</span>
                        </div>
                    </div>`;
            });
            list.innerHTML = html || '<p class="text-xs text-slate-400 py-4 text-center">No products found.</p>';
        }

        function filterInventory(type) {
            currentInvFilter = type;
            ['All', 'Low', 'expired_soon'].forEach(f => {
                let btn = document.getElementById('inv-filter-' + f);
                if (btn) {
                    if (f === type) {
                        btn.className = "px-3.5 py-1.5 rounded-xl text-xs font-bold bg-indigo-600 text-white obsidian-key";
                    } else {
                        btn.className = "px-3.5 py-1.5 rounded-xl text-xs font-bold bg-slate-100 dark:bg-[#12151C] text-slate-400 border-2 border-slate-300 dark:border-obsidianBorder obsidian-key";
                    }
                }
            });
            renderInventory();
        }

        function populateQsProducts() {
            let select = document.getElementById('qs-product-select');
            select.innerHTML = products.map(p => `<option value="${p.id}" ${p.id === selectedQsProductId ? 'selected' : ''}>${p.name} ₱${p.price}/${p.unit}</option>`).join('');
        }

        function onQsProductChange() {
            selectedQsProductId = document.getElementById('qs-product-select').value;
            updateQuickSell();
        }

        function setQsMode(mode) {
            qsMode = mode;
            let btnKilo = document.getElementById('qs-btn-kilo');
            let btnAmount = document.getElementById('qs-btn-amount');
            let label = document.getElementById('qs-input-label');

            if (mode === 'kilo') {
                btnKilo.className = "flex-1 py-2 rounded-xl text-xs font-bold bg-indigo-600 text-white obsidian-key";
                btnAmount.className = "flex-1 py-2 rounded-xl text-xs font-bold text-slate-400 obsidian-key";
                label.textContent = "KILOS";
            } else {
                btnAmount.className = "flex-1 py-2 rounded-xl text-xs font-bold bg-indigo-600 text-white obsidian-key";
                btnKilo.className = "flex-1 py-2 rounded-xl text-xs font-bold text-slate-400 obsidian-key";
                label.textContent = "AMOUNT IN PESOS (₱)";
            }
            updateQuickSell();
        }

        function updateQuickSell() {
            let prod = products.find(p => p.id === selectedQsProductId) || products[0];
            let val = parseFloat(document.getElementById('qs-value-input').value) || 0;
            document.getElementById('qs-stock-display').textContent = `Stock: ${prod.stock} ${prod.unit}`;

            let totalAmount = qsMode === 'kilo' ? val * prod.price : val;
            let kilos = qsMode === 'kilo' ? val : (prod.price > 0 ? val / prod.price : 0);

            document.getElementById('qs-formula').textContent = `${kilos.toFixed(2)} ${prod.unit} × ₱${prod.price}`;
            document.getElementById('qs-total').textContent = `₱${totalAmount.toLocaleString()}`;
        }

        function executeQuickSell(type) {
            let prod = products.find(p => p.id === selectedQsProductId) || products[0];
            let val = parseFloat(document.getElementById('qs-value-input').value) || 0;
            if (val <= 0) return;

            let customer = document.getElementById('qs-customer').value.trim() || 'Walk-in Customer';
            let totalAmount = qsMode === 'kilo' ? val * prod.price : val;
            let kilos = qsMode === 'kilo' ? val : (prod.price > 0 ? val / prod.price : 0);
            prod.stock = Math.max(0, prod.stock - kilos);

            let txId = 'TX-' + Math.floor(1000 + Math.random() * 9000);
            let now = new Date();
            let todayDate = now.toISOString().split('T')[0] + ' ' + now.toTimeString().split(' ')[0];
            let itemDesc = `${prod.name} (${kilos.toFixed(2)} ${prod.unit})`;

            transactions.unshift({
                id: txId, date: todayDate, customer, items: itemDesc, amount: totalAmount, cogs: prod.cost * kilos, cash: totalAmount, change: 0, type
            });

            openReceiptModal(txId, customer, itemDesc, totalAmount, totalAmount, 0, type, todayDate);

            closeQuickSellModal();
            renderTransactions();
            renderRecentSales();
            renderInventory();
            renderDashboard();
            renderUtang();
            renderPLReport();
        }

        function openQuickSellModal() { populateQsProducts(); document.getElementById('quicksell-modal').classList.remove('hidden'); updateQuickSell(); }
        function closeQuickSellModal() { document.getElementById('quicksell-modal').classList.add('hidden'); }

        function filterUtang(type) {
            utangFilter = type;
            let btnBal = document.getElementById('utang-filter-bal');
            let btnAll = document.getElementById('utang-filter-all');
            if (type === 'balance') {
                btnBal.className = "px-4 py-1.5 rounded-xl text-xs font-bold bg-indigo-600 text-white obsidian-key";
                btnAll.className = "px-4 py-1.5 rounded-xl text-xs font-bold bg-white dark:bg-obsidianCard text-slate-400 border-2 border-slate-300 dark:border-obsidianBorder obsidian-key";
            } else {
                btnAll.className = "px-4 py-1.5 rounded-xl text-xs font-bold bg-indigo-600 text-white obsidian-key";
                btnBal.className = "px-4 py-1.5 rounded-xl text-xs font-bold bg-white dark:bg-obsidianCard text-slate-400 border-2 border-slate-300 dark:border-obsidianBorder obsidian-key";
            }
            renderUtang();
        }

        function renderUtang() {
            let container = document.getElementById('utang-list-container');
            let query = (document.getElementById('utang-search')?.value || '').toLowerCase();
            
            let ledger = {};
            transactions.filter(t => t.type === 'Utang').forEach(t => {
                let name = t.customer || 'Unknown';
                if (!ledger[name]) ledger[name] = { totalUtang: 0, records: [] };
                ledger[name].totalUtang += t.amount;
                ledger[name].records.push(t);
            });

            let totalUncollected = Object.values(ledger).reduce((sum, cust) => sum + cust.totalUtang, 0);
            document.getElementById('total-utang-display').textContent = '₱' + totalUncollected.toLocaleString();

            let html = '';
            let custNames = Object.keys(ledger);

            if (custNames.length === 0) {
                container.innerHTML = `<div class="p-6 bg-white dark:bg-obsidianCard border-2 border-slate-300 dark:border-obsidianBorder rounded-3xl text-center obsidian-key"><p class="text-xs text-slate-400">No active utang records found.</p></div>`;
                return;
            }

            custNames.forEach(name => {
                if (query && !name.toLowerCase().includes(query)) return;
                let data = ledger[name];
                if (utangFilter === 'balance' && data.totalUtang <= 0) return;

                html += `
                    <div class="p-4 bg-white dark:bg-obsidianCard border-2 border-slate-300 dark:border-obsidianBorder rounded-3xl space-y-3 obsidian-key">
                        <div class="flex justify-between items-center">
                            <div>
                                <h4 class="font-black text-sm text-indigo-400">${name}</h4>
                                <span class="text-[10px] text-slate-400 font-bold">${data.records.length} purchase record(s)</span>
                            </div>
                            <div class="text-right">
                                <span class="text-base font-black text-amber-400">₱${data.totalUtang.toLocaleString()}</span>
                                <button onclick="openSettleModal('${name}', ${data.totalUtang})" class="block mt-1 bg-emerald-500/20 text-emerald-400 font-bold px-3 py-1 rounded-xl text-[10px] obsidian-key ml-auto">Settle / Pay</button>
                            </div>
                        </div>
                        <div class="space-y-1.5 pt-2 border-t border-slate-200 dark:border-obsidianBorder/60 text-xs">
                `;

                data.records.forEach(r => {
                    html += `
                        <div class="flex justify-between items-center text-[11px]">
                            <span class="text-slate-400">${r.date} — ${r.items}</span>
                            <span class="font-bold text-slate-200">₱${r.amount.toLocaleString()}</span>
                        </div>
                    `;
                });

                html += `</div></div>`;
            });

            container.innerHTML = html || `<div class="p-6 bg-white dark:bg-obsidianCard border-2 border-slate-300 dark:border-obsidianBorder rounded-3xl text-center obsidian-key"><p class="text-xs text-slate-400">No matching customers found.</p></div>`;
        }

        function openSettleModal(customerName, balance) {
            document.getElementById('su-customer').value = customerName;
            document.getElementById('su-customer-name').textContent = customerName;
            document.getElementById('su-balance-display').textContent = '₱' + balance.toLocaleString();
            document.getElementById('su-payment').value = balance;
            document.getElementById('settle-utang-modal').classList.remove('hidden');
        }

        function closeSettleModal() {
            document.getElementById('settle-utang-modal').classList.add('hidden');
        }

        function confirmSettleUtang() {
            let customerName = document.getElementById('su-customer').value;
            let payment = parseFloat(document.getElementById('su-payment').value) || 0;
            if (payment <= 0) return;

            transactions.forEach(t => {
                if (t.customer === customerName && t.type === 'Utang') {
                    t.type = 'Paid';
                    t.cash = t.amount;
                }
            });

            closeSettleModal();
            renderUtang();
            renderTransactions();
            renderDashboard();
            renderPLReport();
            showToast(`Utang settled for ${customerName}!`);
        }

        function openEditTxModal(id) {
            if (currentRole !== 'Admin') {
                showToast("Access Denied: Admin authorization required.");
                return;
            }
            let tx = transactions.find(t => t.id === id);
            if (!tx) return;
            document.getElementById('etx-id').value = tx.id;
            document.getElementById('etx-date').value = tx.date;
            document.getElementById('etx-customer').value = tx.customer;
            document.getElementById('etx-items').value = tx.items;
            document.getElementById('etx-amount').value = tx.amount;
            document.getElementById('etx-cash').value = tx.cash || tx.amount;
            document.getElementById('etx-change').value = tx.change || 0;
            document.getElementById('etx-type').value = tx.type;
            document.getElementById('edit-tx-modal').classList.remove('hidden');
        }

        function closeEditTxModal() { document.getElementById('edit-tx-modal').classList.add('hidden'); }

        function deleteTransaction(id) {
            if (currentRole !== 'Admin') {
                showToast("Access Denied: Admin authorization required.");
                return;
            }
            if (confirm("Delete this transaction?")) {
                transactions = transactions.filter(t => t.id !== id);
                renderTransactions();
                renderRecentSales();
                renderDashboard();
                renderUtang();
                renderPLReport();
                showToast("Transaction deleted.");
            }
        }

        function saveTxEdit() {
            if (currentRole !== 'Admin') {
                showToast("Access Denied: Admin authorization required.");
                return;
            }
            let id = document.getElementById('etx-id').value;
            let tx = transactions.find(t => t.id === id);
            if (tx) {
                tx.date = document.getElementById('etx-date').value;
                tx.customer = document.getElementById('etx-customer').value;
                tx.items = document.getElementById('etx-items').value;
                tx.amount = parseFloat(document.getElementById('etx-amount').value) || 0;
                tx.cash = parseFloat(document.getElementById('etx-cash').value) || tx.amount;
                tx.change = parseFloat(document.getElementById('etx-change').value) || 0;
                tx.type = document.getElementById('etx-type').value;

                renderTransactions();
                renderRecentSales();
                renderDashboard();
                renderUtang();
                renderPLReport();
                closeEditTxModal();
                showToast("Transaction updated!");
            }
        }

        function getItemPriceFromDb(itemName) {
            let clean = itemName.split(' x')[0].split(' (')[0].trim();
            let p = products.find(prod => clean.toLowerCase().includes(prod.name.toLowerCase()) || prod.name.toLowerCase().includes(clean.toLowerCase()));
            if (p) return p.price;
            return null;
        }

        function openReceiptModal(id, customer, itemsStr, total, cash, change, type, dateStr) {
            document.getElementById('rcpt-id').textContent = id;
            document.getElementById('rcpt-date').textContent = dateStr;
            document.getElementById('rcpt-customer').textContent = customer || 'Walk-in Customer';
            document.getElementById('rcpt-type').textContent = type === 'Paid' ? 'Paid Cash' : type;
            document.getElementById('rcpt-total').textContent = '₱' + total.toLocaleString();
            document.getElementById('rcpt-cash').textContent = '₱' + cash.toLocaleString();
            document.getElementById('rcpt-change').textContent = '₱' + change.toLocaleString();

            let itemsList = document.getElementById('rcpt-items-breakdown');
            let itemParts = itemsStr.split(', ');
            let html = '';

            itemParts.forEach(itemStr => {
                let qty = 1;
                let namePart = itemStr;
                if (itemStr.includes(' x')) {
                    let parts = itemStr.split(' x');
                    namePart = parts[0];
                    qty = parseFloat(parts[1]) || 1;
                }

                let unitPrice = getItemPriceFromDb(namePart);
                let itemTotal = unitPrice ? (unitPrice * qty) : null;
                let priceDisplay = itemTotal ? '₱' + itemTotal.toLocaleString() : 'Item Price';

                html += `
                    <div class="flex justify-between items-center py-1.5 border-b border-slate-200 dark:border-obsidianBorder/50">
                        <span class="text-slate-900 dark:text-slate-100 font-bold">${itemStr}</span>
                        <span class="text-emerald-400 font-extrabold font-mono text-right ml-2">${priceDisplay}</span>
                    </div>`;
            });

            itemsList.innerHTML = html;
            document.getElementById('receipt-modal').classList.remove('hidden');
        }

        function saveReceiptToGallery() {
            let receiptElement = document.getElementById('receipt-card-content');
            let txId = document.getElementById('rcpt-id').textContent || 'Receipt';
            
            html2canvas(receiptElement, {
                scale: 2,
                useCORS: true,
                backgroundColor: null
            }).then(canvas => {
                let imageURL = canvas.toDataURL('image/png');
                let downloadLink = document.createElement('a');
                downloadLink.href = imageURL;
                downloadLink.download = `${txId}-IbañezStore.png`;
                document.body.appendChild(downloadLink);
                downloadLink.click();
                document.body.removeChild(downloadLink);
                showToast("Receipt saved to gallery!");
            }).catch(err => {
                console.error("Error saving receipt:", err);
                showToast("Failed to save receipt image.");
            });
        }

        function viewTxReceipt(id) {
            let tx = transactions.find(t => t.id === id);
            if (tx) {
                openReceiptModal(tx.id, tx.customer, tx.items, tx.amount, tx.cash || tx.amount, tx.change || 0, tx.type, tx.date);
            }
        }

        function renderTransactions() {
            let list = document.getElementById('full-transactions-list');
            let query = (document.getElementById('tx-search')?.value || '').toLowerCase();
            let dateFrom = document.getElementById('tx-date-from')?.value || '';
            let dateTo = document.getElementById('tx-date-to')?.value || '';

            let filtered = transactions.filter(t => {
                if (currentTxFilter === 'Sales' && t.type !== 'Paid') return false;
                if (currentTxFilter === 'Utang' && t.type !== 'Utang') return false;
                if (currentTxFilter === 'Expenses' && t.type !== 'Expense') return false;
                if (query && !t.customer.toLowerCase().includes(query) && !t.items.toLowerCase().includes(query)) return false;
                
                let txDateOnly = t.date.split(' ')[0];
                if (dateFrom && txDateOnly < dateFrom) return false;
                if (dateTo && txDateOnly > dateTo) return false;

                return true;
            });

            let totalFilteredSum = filtered.reduce((sum, t) => sum + t.amount, 0);
            document.getElementById('tx-summary-val').textContent = '₱' + totalFilteredSum.toLocaleString();
            document.getElementById('tx-summary-count').textContent = `${filtered.length} matching records`;

            let html = '';
            filtered.forEach(t => {
                html += `
                    <div class="p-4 bg-slate-100 dark:bg-[#12151C] border-2 border-slate-300 dark:border-obsidianBorder rounded-3xl space-y-2 obsidian-key">
                        <div class="flex justify-between items-start">
                            <div>
                                <h4 class="font-extrabold text-sm">${t.date} | ${t.customer}</h4>
                                <p class="text-xs text-slate-400">${t.items}</p>
                            </div>
                            <div class="text-right">
                                <span class="font-black text-base ${t.type === 'Expense' ? 'text-rose-500' : 'text-emerald-400'}">₱${t.amount.toLocaleString()}</span>
                                <span class="block text-[10px] font-bold text-slate-400">${t.type}</span>
                            </div>
                        </div>
                        <div class="flex justify-end gap-2 pt-1 border-t border-slate-200 dark:border-obsidianBorder/60">
                            <button onclick="viewTxReceipt('${t.id}')" class="bg-emerald-500/10 text-emerald-400 font-black px-3 py-1 rounded-xl text-xs obsidian-key flex items-center gap-1">
                                <i class="fa-solid fa-receipt text-[11px]"></i> View Receipt
                            </button>
                            ${currentRole === 'Admin' ? `
                            <button onclick="openEditTxModal('${t.id}')" class="bg-indigo-500/10 text-indigo-400 font-bold px-3 py-1 rounded-xl text-xs obsidian-key">Edit</button>
                            <button onclick="deleteTransaction('${t.id}')" class="bg-rose-500/10 text-rose-500 font-bold px-3 py-1 rounded-xl text-xs obsidian-key">Delete</button>` : ''}
                        </div>
                    </div>`;
            });
            list.innerHTML = html || '<p class="text-xs text-slate-400 py-4 text-center">No transactions found.</p>';
        }

        function filterTransactions(type) {
            currentTxFilter = type;
            ['All', 'Sales', 'Utang', 'Expenses'].forEach(f => {
                let btn = document.getElementById('tx-filter-' + f);
                if (btn) btn.className = (f === type) ? "px-4 py-1.5 rounded-xl text-xs font-bold bg-indigo-600 text-white whitespace-nowrap obsidian-key" : "px-4 py-1.5 rounded-xl text-xs font-bold bg-slate-100 dark:bg-[#12151C] text-slate-400 border-2 border-slate-300 dark:border-obsidianBorder whitespace-nowrap obsidian-key";
            });
            renderTransactions();
        }

        function renderRecentSales() {
            let container = document.getElementById('dash-recent-list');
            let html = '';
            transactions.filter(t => t.type !== 'Expense').slice(0, 3).forEach(t => {
                html += `
                    <div class="p-4 bg-white dark:bg-obsidianCard border-2 border-slate-300 dark:border-obsidianBorder rounded-3xl flex justify-between items-center obsidian-key">
                        <div>
                            <h4 class="font-bold text-sm">${t.date} | ${t.customer}</h4>
                            <p class="text-xs text-slate-400">${t.items}</p>
                        </div>
                        <div class="text-right">
                            <span class="font-black text-sm text-emerald-400 block">₱${t.amount.toLocaleString()}</span>
                        </div>
                    </div>`;
            });
            container.innerHTML = html || '<p class="text-xs text-slate-400 text-center">No sales yet.</p>';
        }

        function renderDashboard() {
            let todayDate = new Date().toISOString().split('T')[0];
            let todaySales = transactions.filter(t => t.date.startsWith(todayDate) && t.type !== 'Expense');
            let todayExpenses = expenses.filter(e => e.date === todayDate);

            let revToday = todaySales.reduce((sum, s) => sum + s.amount, 0);
            let cogsToday = todaySales.reduce((sum, s) => sum + (s.cogs || 0), 0);
            let grossProfitToday = revToday - cogsToday;
            let grossProfitPctToday = revToday > 0 ? (grossProfitToday / revToday) * 100 : 0;
            let expToday = todayExpenses.reduce((sum, e) => sum + e.amount, 0);
            let netWinLoss = grossProfitToday - expToday;

            document.getElementById('dash-today-sales').textContent = '₱' + revToday.toLocaleString();
            document.getElementById('dash-today-count').textContent = `${todaySales.length} sales`;
            document.getElementById('dash-revenue').textContent = '₱' + revToday.toLocaleString();
            document.getElementById('dash-profit').textContent = '₱' + grossProfitToday.toLocaleString();
            document.getElementById('dash-profit-pct').textContent = `(${grossProfitPctToday.toFixed(1)}%)`;
            document.getElementById('dash-net-winloss').textContent = '₱' + netWinLoss.toLocaleString();
        }

        function renderPLReport() {
            let totalMonthlyProfit = transactions.filter(t => t.type !== 'Expense').reduce((sum, t) => sum + (t.amount - (t.cogs || 0)), 0);
            let totalMonthlyNet = totalMonthlyProfit - expenses.reduce((sum, e) => sum + e.amount, 0);

            document.getElementById('pl-monthly-profit').textContent = '₱' + totalMonthlyProfit.toLocaleString();
            document.getElementById('pl-monthly-net').textContent = '₱' + totalMonthlyNet.toLocaleString();

            let rent = parseFloat(document.getElementById('be-rent').value) || 0;
            let salary = parseFloat(document.getElementById('be-salary').value) || 0;
            let electricity = parseFloat(document.getElementById('be-electricity').value) || 0;
            let water = parseFloat(document.getElementById('be-water').value) || 0;
            let permits = parseFloat(document.getElementById('be-permits').value) || 0;
            let delivery = parseFloat(document.getElementById('be-delivery').value) || 0;

            let overheadTarget = rent + salary + electricity + water + permits + delivery;
            let gap = overheadTarget - totalMonthlyProfit;
            let coveragePct = overheadTarget > 0 ? Math.min(100, Math.max(0, (totalMonthlyProfit / overheadTarget) * 100)) : 0;

            document.getElementById('pl-overhead-pct').textContent = coveragePct.toFixed(1) + '% Covered';
            document.getElementById('pl-overhead-progress-bar').style.width = coveragePct.toFixed(1) + '%';
            document.getElementById('pl-overhead-target-lbl').textContent = 'Target: =monthly overhead cost (₱' + overheadTarget.toLocaleString() + ')';

            let remEl = document.getElementById('pl-overhead-remaining');
            if (gap > 0) {
                remEl.textContent = '₱' + gap.toLocaleString('en-US', {minimumFractionDigits: 2}) + ' Needed';
                remEl.className = "text-2xl font-black text-rose-500";
            } else {
                remEl.textContent = '+₱' + Math.abs(gap).toLocaleString('en-US', {minimumFractionDigits: 2}) + ' Surplus';
                remEl.className = "text-2xl font-black text-emerald-400";
            }
        }

        function filterPOSCategory(cat) {
            currentPosCategory = cat;
            ['All', 'Dairy', 'Canned', 'Drinks', 'Grains', 'Noodles', 'Snacks', 'Beverages', 'Condiments', 'Pantry'].forEach(c => {
                let btn = document.getElementById('pos-cat-' + c);
                if (btn) btn.className = (c === cat) ? "pos-cat-btn px-4 py-1.5 rounded-xl text-xs font-bold bg-indigo-600 text-white whitespace-nowrap obsidian-key" : "pos-cat-btn px-4 py-1.5 rounded-xl text-xs font-bold bg-white dark:bg-obsidianCard text-slate-400 border-2 border-slate-300 dark:border-obsidianBorder whitespace-nowrap obsidian-key";
            });
            renderPOSGrid();
        }

        function renderPOSGrid() {
            let html = '';
            let searchQuery = (document.getElementById('pos-search')?.value || '').toLowerCase();

            let filtered = products.filter(p => {
                if (currentPosCategory !== 'All' && p.category !== currentPosCategory) return false;
                if (searchQuery && !p.name.toLowerCase().includes(searchQuery)) return false;
                return true;
            });

            filtered.forEach(p => {
                let cartQty = cart[p.id] ? cart[p.id].qty : 0;
                html += `
                    <div onclick="addToCart('${p.id}')" class="p-4 bg-white dark:bg-obsidianCard border-2 ${cartQty > 0 ? 'border-indigo-500' : 'border-slate-300 dark:border-obsidianBorder'} rounded-3xl cursor-pointer relative space-y-1 obsidian-key">
                        ${cartQty > 0 ? `<div class="absolute top-3 right-3 w-6 h-6 rounded-full bg-indigo-600 text-white font-black text-xs flex items-center justify-center">${cartQty}</div>` : ''}
                        <h4 class="font-bold text-sm pr-6 leading-snug">${p.name}</h4>
                        <div class="text-emerald-400 font-bold text-sm">₱${p.price.toLocaleString()}</div>
                        <p class="text-[11px] text-slate-400 font-medium">${p.stock} ${p.unit}</p>
                    </div>`;
            });
            document.getElementById('pos-products-grid').innerHTML = html;
        }

        function addToCart(id) {
            let p = products.find(prod => prod.id === id);
            if (!cart[id]) cart[id] = { name: p.name, price: p.price, cost: p.cost, qty: 1 };
            else cart[id].qty += 1;
            renderPOSGrid();
            renderCart();
        }

        function changeQty(id, delta) {
            if (cart[id]) {
                cart[id].qty += delta;
                if (cart[id].qty <= 0) delete cart[id];
            }
            renderPOSGrid();
            renderCart();
        }

        function clearCart() {
            cart = {};
            document.getElementById('pos-cash-input').value = '';
            renderPOSGrid();
            renderCart();
            showToast("Cart cleared");
        }

        function renderCart() {
            let list = document.getElementById('pos-cart-list');
            let keys = Object.keys(cart);
            let total = 0;

            if (keys.length === 0) {
                list.innerHTML = '<p class="text-xs text-slate-400 py-2">No items in cart.</p>';
                document.getElementById('pos-total-display').textContent = '₱0';
                document.getElementById('pos-change-row').classList.add('hidden');
                return;
            }

            let html = '';
            keys.forEach(id => {
                let item = cart[id];
                let subtotal = item.price * item.qty;
                total += subtotal;
                html += `
                    <div class="flex justify-between items-center py-1 border-b border-slate-200 dark:border-obsidianBorder">
                        <div>
                            <span class="font-bold text-sm block">${item.name}</span>
                            <span class="text-xs text-slate-400">₱${item.price} × ${item.qty} = ₱${subtotal}</span>
                        </div>
                        <div class="flex items-center gap-2">
                            <button onclick="changeQty('${id}', -1)" class="w-7 h-7 rounded-lg bg-slate-200 dark:bg-obsidianBorder font-black obsidian-key">-</button>
                            <span class="font-bold text-sm w-4 text-center">${item.qty}</span>
                            <button onclick="changeQty('${id}', 1)" class="w-7 h-7 rounded-lg bg-slate-200 dark:bg-obsidianBorder font-black obsidian-key">+</button>
                        </div>
                    </div>`;
            });
            list.innerHTML = html;
            document.getElementById('pos-total-display').textContent = '₱' + total.toLocaleString();
            updatePOSCalculations();
        }

        function updatePOSCalculations() {
            let total = Object.values(cart).reduce((sum, item) => sum + (item.price * item.qty), 0);
            let cash = parseFloat(document.getElementById('pos-cash-input').value) || 0;
            let changeRow = document.getElementById('pos-change-row');

            if (cash > 0 && total > 0) {
                let change = cash - total;
                changeRow.classList.remove('hidden');
                document.getElementById('pos-change-val').textContent = '₱' + (change >= 0 ? change.toLocaleString() : '0');
            } else {
                changeRow.classList.add('hidden');
            }
        }

        function checkout(type) {
            let keys = Object.keys(cart);
            if (keys.length === 0) return;

            let total = 0, totalCogs = 0;
            keys.forEach(k => {
                let prod = products.find(p => p.id === k);
                if (prod) {
                    total += prod.price * cart[k].qty;
                    totalCogs += prod.cost * cart[k].qty;
                    prod.stock = Math.max(0, prod.stock - cart[k].qty);
                }
            });

            let cash = parseFloat(document.getElementById('pos-cash-input').value) || total;
            let change = Math.max(0, cash - total);
            let customer = document.getElementById('pos-customer-input').value.trim() || 'Walk-in Customer';
            let itemSummary = keys.map(k => `${cart[k].name} x${cart[k].qty}`).join(', ');
            let txId = 'TX-' + Math.floor(1000 + Math.random() * 9000);
            
            let now = new Date();
            let todayDate = now.toISOString().split('T')[0] + ' ' + now.toTimeString().split(' ')[0];

            transactions.unshift({
                id: txId, date: todayDate, customer, items: itemSummary, amount: total, cogs: totalCogs, cash, change, type
            });

            openReceiptModal(txId, customer, itemSummary, total, cash, change, type, todayDate);

            clearCart();
            renderTransactions();
            renderRecentSales();
            renderInventory();
            renderDashboard();
            renderUtang();
            renderPLReport();
        }

        function closeReceiptModal() {
            document.getElementById('receipt-modal').classList.add('hidden');
        }

        function showToast(msg) {
            const toast = document.getElementById('top-toast');
            document.getElementById('top-toast-msg').textContent = msg;
            toast.classList.remove('hidden');
            setTimeout(() => toast.classList.add('hidden'), 4000);
        }

        function calcMarginFormula() {
            let sell = parseFloat(document.getElementById('bm-sell').value) || 0;
            let cost = parseFloat(document.getElementById('bm-cost').value) || 0;
            let marginPct = sell > 0 ? ((sell - cost) / sell) * 100 : 0;

            document.getElementById('bm-formula-txt').textContent = `(${sell} - ${cost}) ÷ ${sell} × 100%`;
            document.getElementById('bm-margin-val').textContent = marginPct.toFixed(1) + '%';
            document.getElementById('be-margin-pct').value = marginPct.toFixed(1);
            calcBreakEven();
        }

        function calcBreakEven() {
            let rent = parseFloat(document.getElementById('be-rent').value) || 0;
            let salary = parseFloat(document.getElementById('be-salary').value) || 0;
            let electricity = parseFloat(document.getElementById('be-electricity').value) || 0;
            let water = parseFloat(document.getElementById('be-water').value) || 0;
            let permits = parseFloat(document.getElementById('be-permits').value) || 0;
            let delivery = parseFloat(document.getElementById('be-delivery').value) || 0;
            let userMargin = parseFloat(document.getElementById('be-margin-pct').value) || 20;

            let totalFixed = rent + salary + electricity + water + permits + delivery;
            let marginDec = userMargin > 0 ? (userMargin / 100) : 0.20;
            let monthlySales = marginDec > 0 ? (totalFixed / marginDec) : 0;
            let dailySales = monthlySales / 30;

            document.getElementById('be-out-total').textContent = '₱' + totalFixed.toLocaleString('en-US', {minimumFractionDigits: 2});
            document.getElementById('be-out-monthly').textContent = '₱' + monthlySales.toLocaleString('en-US', {minimumFractionDigits: 2});
            document.getElementById('be-out-daily').textContent = '₱' + dailySales.toLocaleString('en-US', {minimumFractionDigits: 2}) + ' / day';

            renderPLReport();
        }

        window.onload = function() {
            updateLiveDateTime();
            applyUserRolePermissions();
            renderPOSGrid();
            renderInventory();
            renderPurchaser();
            renderExpenses();
            renderTransactions();
            renderRecentSales();
            renderDashboard();
            renderUtang();
            calcMarginFormula();
            calcBreakEven();
        }
    </script>
</body>
</html>
"""

class StoreHandler(http.server.BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path == '/' or self.path == '/index.html':
            self.send_response(200)
            self.send_header("Content-type", "text/html; charset=utf-8")
            self.end_headers()
            self.wfile.write(HTML_CONTENT.encode("utf-8"))
        else:
            self.send_response(404)
            self.end_headers()

    def log_message(self, format, *args):
        pass

def run_server():
    socketserver.TCPServer.allow_reuse_address = True
    with socketserver.TCPServer(("0.0.0.0", PORT), StoreHandler) as httpd:
        httpd.serve_forever()

if __name__ == '__main__':
    server_thread = threading.Thread(target=run_server, daemon=True)
    server_thread.start()
    webbrowser.open(f"http://127.0.0.1:{PORT}")
    print("\n=======================================================")
    print(f"  Ibañez Vault Store App is running!")
    print(f"  Local Device Link : http://127.0.0.1:{PORT}")
    print(f"  Any Phone/Device Link: http://{LOCAL_IP}:{PORT}")
    print("=======================================================\n")
    try:
        while True:
            threading.Event().wait(1)
    except KeyboardInterrupt:
        pass
