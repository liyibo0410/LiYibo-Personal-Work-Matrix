"use client";

import { useState } from "react";

export default function Home() {
    const [name, setName] = useState("低糖燕麦饼干");

    return (
        <div className="min-h-screen bg-gradient-to-br from-slate-50 to-slate-100 flex items-center justify-center p-6">
            <div className="w-full max-w-lg bg-white rounded-3xl shadow-2xl shadow-slate-200/60 p-8 transition-all duration-300 hover:shadow-slate-300/80">

                {/* 头部装饰 */}
                <div className="flex items-center gap-2 mb-2">
                    <span className="h-1 w-8 rounded-full bg-gradient-to-r from-amber-400 to-orange-400"></span>
                    <span className="h-1 w-4 rounded-full bg-amber-300"></span>
                </div>

                <h1 className="text-3xl font-bold bg-gradient-to-r from-slate-800 to-slate-600 bg-clip-text text-transparent mb-1 tracking-tight">
                    🛍️ 电商运营练习
                </h1>
                <p className="text-slate-400 text-sm mb-8 font-medium tracking-wide">
                    实时编辑 · 即时预览
                </p>

                {/* 输入卡片 */}
                <div className="space-y-2">
                    <label htmlFor="productName" className="text-sm font-semibold text-slate-700 flex items-center gap-2">
                        <span className="text-amber-500">✏️</span>
                        商品名称
                    </label>
                    <div className="relative">
                        <input
                            id="productName"
                            type="text"
                            value={name}
                            onChange={(event) => setName(event.target.value)}
                            className="w-full px-5 py-3.5 bg-slate-50 border-2 border-slate-200 rounded-2xl text-slate-800 text-base font-medium outline-none transition-all duration-200 focus:border-amber-400 focus:bg-white focus:shadow-[0_0_0_4px_rgba(251,191,36,0.15)] placeholder:text-slate-300"
                            placeholder="输入商品名称..."
                            autoComplete="off"
                        />
                        <div className="absolute right-4 top-1/2 -translate-y-1/2 text-slate-300 text-sm font-mono">
                            {name.length}
                        </div>
                    </div>
                </div>

                {/* 商品预览卡片 */}
                <div className="mt-8 p-5 bg-gradient-to-br from-amber-50 to-orange-50/50 rounded-2xl border border-amber-200/60 transition-all duration-300">
                    <div className="flex items-center gap-4">
                        {/* 商品图标 */}
                        <div className="w-14 h-14 rounded-2xl bg-gradient-to-br from-amber-400 to-orange-400 flex items-center justify-center text-2xl shadow-lg shadow-amber-400/30 flex-shrink-0">
                            🍪
                        </div>
                        <div className="flex-1 min-w-0">
                            <p className="text-xs text-amber-600/70 font-semibold tracking-widest uppercase">
                                当前商品
                            </p>
                            <p className="text-xl font-bold text-slate-800 truncate transition-colors duration-200">
                                {name || <span className="text-slate-300 font-normal">未命名商品</span>}
                            </p>
                        </div>
                        {/* 状态标签 */}
                        <span className="px-3 py-1 bg-white/80 backdrop-blur-sm rounded-full text-xs font-bold text-emerald-600 border border-emerald-200/60 shadow-sm">
                            ● 已上架
                        </span>
                    </div>
                </div>

                {/* 底部操作提示 */}
                <div className="mt-6 flex items-center justify-between text-xs text-slate-400">
                    <span className="flex items-center gap-1.5">
                        <span className="w-1.5 h-1.5 rounded-full bg-emerald-400"></span>
                        实时同步
                    </span>
                    <span className="font-mono bg-slate-100 px-3 py-1 rounded-full text-slate-500">
                        {name ? `“${name}”` : '等待输入…'}
                    </span>
                </div>
            </div>
        </div>
    );
}