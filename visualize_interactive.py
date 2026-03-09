"""
ETF套利分析 - 交互式可视化（优化交互版）
使用Plotly生成交互式HTML文件
优化缩放、滚动、平移等交互体验
"""

import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from pathlib import Path
from datetime import datetime
import json
import numpy as np


def load_config():
    """加载配置文件"""
    config_path = Path("config.json")
    if config_path.exists():
        with open(config_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    return None


def load_data(etf_codes):
    """加载ETF数据"""
    data = {}
    
    for code in etf_codes:
        file_path = Path(f"data/{code}_premium.csv")
        if file_path.exists():
            df = pd.read_csv(file_path)
            df['日期'] = pd.to_datetime(df['日期'])
            data[code] = df
    
    return data


def load_tracking_error_data(etf_codes):
    """加载ETF跟踪误差数据"""
    data = {}
    
    for code in etf_codes:
        file_path = Path(f"data/{code}_tracking_error.csv")
        if file_path.exists():
            df = pd.read_csv(file_path)
            df['日期'] = pd.to_datetime(df['日期'])
            data[code] = df
    
    return data


def calculate_r_squared_data(etf_codes):
    """计算并返回各ETF的跟踪精度"""
    import numpy as np
    
    r_squared_dict = {}
    
    for code in etf_codes:
        file_path = Path(f"data/{code}_tracking_error.csv")
        if file_path.exists():
            df = pd.read_csv(file_path)
            
            if len(df) < 2:
                continue
            
            # 删除NaN
            df = df.dropna()
            
            if len(df) < 2:
                continue
            
            # 计算R²
            y = np.array(df['ETF净值涨幅'])
            x = np.array(df['指数涨跌幅'])
            
            correlation = np.corrcoef(x, y)[0, 1]
            r_squared = correlation ** 2
            r_squared_dict[code] = r_squared
    
    # 按R²排序
    sorted_r2 = sorted(r_squared_dict.items(), key=lambda x: x[1], reverse=True)
    
    return sorted_r2


def create_tracking_error_chart(data, index_name="指数", title="ETF跟踪误差走势"):
    """创建跟踪误差对比图（相对于指定指数）"""
    
    if not data:
        return None
    
    fig = go.Figure()
    colors = ['#1f77b4', '#ff7f0e', '#2ca02c', '#d62728', '#9467bd', '#8c564b']
    
    for i, (code, df) in enumerate(data.items()):
        fig.add_trace(go.Scatter(
            x=df['日期'],
            y=df['跟踪误差'],
            mode='lines',
            name=f'{code}',
            line=dict(color=colors[i % len(colors)], width=2),
            hovertemplate=(
                f'<b>{code}</b><br>' +
                '日期: %{x|%Y-%m-%d}<br>' +
                'ETF净值涨幅: %{customdata[0]:.2f}%<br>' +
                '指数涨跌幅: %{customdata[1]:.2f}%<br>' +
                '跟踪误差: %{y:.2f}%<br>' +
                '<extra></extra>'
            ),
            customdata=df[['ETF净值涨幅', '指数涨跌幅']].values
        ))
    
    fig.add_hline(y=0, line_dash="solid", line_color="gray", opacity=0.7)
    
    fig.update_layout(
        title={
            'text': title,
            'x': 0.5,
            'xanchor': 'center',
            'font': dict(size=18)
        },
        xaxis_title='日期',
        yaxis_title='跟踪误差 (%)',
        hovermode='x unified',
        template='plotly_white',
        height=500,
        dragmode='pan',
        legend=dict(
            orientation="h",
            yanchor="bottom",
            y=1.05,
            xanchor="right",
            x=1,
            bgcolor='rgba(255,255,255,0.8)'
        ),
        xaxis=dict(
            type="date",
            tickformat='%Y-%m-%d',
            tickfont=dict(size=10),
            gridcolor='rgba(0,0,0,0.1)'
        ),
        yaxis=dict(
            tickformat='.2f',
            tickfont=dict(size=10),
            gridcolor='rgba(0,0,0,0.1)',
            zerolinecolor='rgba(0,0,0,0.3)'
        ),
        hoverlabel=dict(
            bgcolor="white",
            font_size=12,
            font_family="Arial"
        )
    )
    
    return fig


def create_etf_vs_index_chart(tracking_data, index_name="指数", title="ETF与指数累计收益对比"):
    """
    创建ETF与指数累计收益对比图（从day0开始归一化）
    
    Args:
        tracking_data: 跟踪误差数据字典，包含ETF净值和指数收盘价格
        index_name: 指数名称
        title: 图表标题
    """
    if not tracking_data:
        return None
    
    import pandas as pd
    import numpy as np
    
    fig = go.Figure()
    
    # ETF使用实线，颜色各不相同
    etf_colors = ['#1f77b4', '#ff7f0e', '#2ca02c', '#d62728', '#9467bd', '#8c564b']
    
    # 获取任意一个ETF的数据来提取指数价格（所有ETF对应的指数数据应该相同）
    first_etf_data = list(tracking_data.values())[0]
    
    # 计算指数的累计收益率（从day0开始归一化到0%）
    index_prices = first_etf_data['收盘'].values
    index_cum_return = [(p / index_prices[0] - 1) * 100 for p in index_prices]
    
    # 添加指数线（虚线，灰色）
    fig.add_trace(go.Scatter(
        x=first_etf_data['日期'],
        y=index_cum_return,
        mode='lines',
        name=f'{index_name}（基准）',
        line=dict(color='#7f7f7f', width=3, dash='dash'),
        hovertemplate=(
            f'<b>{index_name}</b><br>' +
            '日期: %{x|%Y-%m-%d}<br>' +
            '累计收益: %{y:.2f}%<br>' +
            '<extra></extra>'
        ),
        opacity=0.9
    ))
    
    # 添加各ETF的累计收益率
    for i, (code, df) in enumerate(tracking_data.items()):
        # 计算ETF的累计收益率
        etf_prices = df['净值'].values
        etf_cum_return = [(p / etf_prices[0] - 1) * 100 for p in etf_prices]
        
        fig.add_trace(go.Scatter(
            x=df['日期'],
            y=etf_cum_return,
            mode='lines',
            name=f'{code}（ETF）',
            line=dict(color=etf_colors[i % len(etf_colors)], width=2.5),
            hovertemplate=(
                f'<b>{code}</b><br>' +
                '日期: %{x|%Y-%m-%d}<br>' +
                '累计收益: %{y:.2f}%<br>' +
                '<extra></extra>'
            )
        ))
    
    # 添加零线（day0基准线）
    fig.add_hline(y=0, line_dash="solid", line_color="black", opacity=0.3, line_width=1)
    
    # 计算Y轴范围，确保所有数据都能良好显示
    all_returns = []
    all_returns.extend(index_cum_return)
    for code, df in tracking_data.items():
        etf_prices = df['净值'].values
        etf_cum_return = [(p / etf_prices[0] - 1) * 100 for p in etf_prices]
        all_returns.extend(etf_cum_return)
    
    y_min, y_max = min(all_returns), max(all_returns)
    y_range = y_max - y_min
    y_padding = y_range * 0.1  # 10% padding
    
    fig.update_layout(
        title={
            'text': title,
            'x': 0.5,
            'xanchor': 'center',
            'font': dict(size=18)
        },
        xaxis_title='日期',
        yaxis_title='累计收益率 (%)',
        hovermode='x unified',
        template='plotly_white',
        height=500,
        dragmode='pan',
        legend=dict(
            orientation="h",
            yanchor="bottom",
            y=1.05,
            xanchor="right",
            x=1,
            bgcolor='rgba(255,255,255,0.8)'
        ),
        xaxis=dict(
            type="date",
            tickformat='%Y-%m-%d',
            tickfont=dict(size=10),
            gridcolor='rgba(0,0,0,0.1)'
        ),
        yaxis=dict(
            tickformat='.2f',
            tickfont=dict(size=10),
            gridcolor='rgba(0,0,0,0.1)',
            zerolinecolor='rgba(0,0,0,0.5)',
            zerolinewidth=2,
            range=[y_min - y_padding, y_max + y_padding]
        ),
        hoverlabel=dict(
            bgcolor="white",
            font_size=12,
            font_family="Arial"
        )
    )
    
    return fig


def create_premium_chart(data, title="ETF溢价率走势"):
    """创建溢价率对比图（优化交互）"""
    
    fig = go.Figure()
    colors = ['#1f77b4', '#ff7f0e', '#2ca02c', '#d62728', '#9467bd', '#8c564b']
    
    for i, (code, df) in enumerate(data.items()):
        fig.add_trace(go.Scatter(
            x=df['日期'],
            y=df['溢价率'],
            mode='lines',
            name=f'{code}',
            line=dict(color=colors[i % len(colors)], width=2),
            hovertemplate=(
                f'<b>{code}</b><br>' +
                '日期: %{x|%Y-%m-%d}<br>' +
                '溢价率: %{y:.2f}%<br>' +
                '价格: %{customdata[0]:.3f}<br>' +
                '净值: %{customdata[1]:.3f}<br>' +
                '<extra></extra>'
            ),
            customdata=df[['收盘', '净值']].values
        ))
    
    # 添加零线
    fig.add_hline(y=0, line_dash="solid", line_color="gray", opacity=0.5)
    
    fig.update_layout(
        title={
            'text': title,
            'x': 0.5,
            'xanchor': 'center',
            'font': dict(size=18)
        },
        xaxis_title='日期',
        yaxis_title='溢价率 (%)',
        hovermode='x unified',
        template='plotly_white',
        height=600,
        dragmode='pan',
        legend=dict(
            orientation="h",
            yanchor="bottom",
            y=1.05,
            xanchor="right",
            x=1,
            bgcolor='rgba(255,255,255,0.8)'
        ),
        xaxis=dict(
            rangeslider=dict(visible=True, thickness=0.05),
            type="date",
            tickformat='%Y-%m-%d',
            tickfont=dict(size=10),
            gridcolor='rgba(0,0,0,0.1)'
        ),
        yaxis=dict(
            tickformat='.1f',
            tickfont=dict(size=10),
            gridcolor='rgba(0,0,0,0.1)',
            zerolinecolor='rgba(0,0,0,0.3)'
        ),
        hoverlabel=dict(
            bgcolor="white",
            font_size=12,
            font_family="Arial"
        )
    )
    
    return fig


def create_all_spread_charts(data, threshold=2.0, chart_title="ETF套利分析"):
    """创建所有ETF对的溢价率差值图（每组共享X轴）"""
    
    etf_codes = list(data.keys())
    charts = []
    
    # 基准ETF依次与后面的ETF对比
    for base_idx in range(len(etf_codes) - 1):
        base_code = etf_codes[base_idx]
        compare_codes = etf_codes[base_idx + 1:]
        
        if len(compare_codes) == 0:
            continue
        
        # 创建子图（同一基准ETF的对比共享X轴）
        fig = make_subplots(
            rows=len(compare_codes),
            cols=1,
            subplot_titles=[f'{base_code} vs {code}' for code in compare_codes],
            vertical_spacing=0.08,
            shared_xaxes=True
        )
        
        df_base = data[base_code]
        colors = ['#e74c3c', '#3498db', '#2ecc71', '#f39c12', '#9b59b6']
        
        for i, code in enumerate(compare_codes, 1):
            df_compare = data[code]
            
            # 合并数据
            merged = pd.merge(
                df_base[['日期', '溢价率', '收盘', '净值']], 
                df_compare[['日期', '溢价率', '收盘', '净值']], 
                on='日期', 
                suffixes=(f'_{base_code}', f'_{code}')
            )
            
            if len(merged) > 0:
                spread = merged[f'溢价率_{base_code}'] - merged[f'溢价率_{code}']
                
                # 添加差值线
                fig.add_trace(go.Scatter(
                    x=merged['日期'],
                    y=spread,
                    mode='lines',
                    name=f'{base_code} vs {code}',
                    line=dict(color=colors[(i-1) % len(colors)], width=2),
                    hovertemplate=(
                        f'<b>{base_code} vs {code}</b><br>' +
                        '日期: %{x|%Y-%m-%d}<br>' +
                        f'{base_code}: ' + '%{customdata[0]:.2f}%<br>' +
                        f'{code}: ' + '%{customdata[1]:.2f}%<br>' +
                        '差值: %{y:.2f}%<br>' +
                        '<extra></extra>'
                    ),
                    customdata=merged[[f'溢价率_{base_code}', f'溢价率_{code}']].values
                ), row=i, col=1)
                
                # 标记套利机会
                mask_above = spread >= threshold
                mask_below = spread <= -threshold
                mask = mask_above | mask_below
                
                if mask.any():
                    fig.add_trace(go.Scatter(
                        x=merged.loc[mask, '日期'],
                        y=spread[mask],
                        mode='markers',
                        name='套利机会' if i == 1 else None,
                        marker=dict(color='red', size=10, symbol='circle'),
                        showlegend=True if i == 1 else False,
                        hovertemplate=(
                            f'<b>套利机会!</b><br>' +
                            '日期: %{x|%Y-%m-%d}<br>' +
                            '差值: %{y:.2f}%<br>' +
                            '<extra></extra>'
                        )
                    ), row=i, col=1)
                
                # 添加阈值线
                fig.add_hline(y=threshold, line_dash="dash", line_color="red", 
                             opacity=0.7, row=i, col=1)
                fig.add_hline(y=-threshold, line_dash="dash", line_color="green",
                             opacity=0.7, row=i, col=1)
                fig.add_hline(y=0, line_dash="solid", line_color="gray",
                             opacity=0.5, row=i, col=1)
                
                # y轴配置
                fig.update_yaxes(
                    tickformat='.1f',
                    gridcolor='rgba(0,0,0,0.1)',
                    zerolinecolor='rgba(0,0,0,0.3)',
                    row=i, col=1
                )
                
                # x轴配置（只在最后一个子图显示）
                fig.update_xaxes(
                    type="date",
                    tickformat='%Y-%m-%d',
                    tickfont=dict(size=10),
                    gridcolor='rgba(0,0,0,0.1)',
                    row=i, col=1
                )
        
        # 设置布局
        fig.update_layout(
            title={
                'text': f'{chart_title} - {base_code}对比分析',
                'x': 0.5,
                'xanchor': 'center',
                'font': dict(size=18)
            },
            height=300 * len(compare_codes) + 80,
            hovermode='x unified',
            template='plotly_white',
            showlegend=True,
            dragmode='pan',
            legend=dict(
                orientation="h",
                yanchor="bottom",
                y=1.02,
                xanchor="right",
                x=1
            ),
            hoverlabel=dict(
                bgcolor="white",
                font_size=12
            )
        )
        
        charts.append({
            'fig': fig,
            'filename': f'chart_spread_{base_code}.html',
            'title': f'{base_code}对比分析'
        })
    
    return charts


def create_spread_chart(data, threshold=2.0, title="ETF溢价率差值"):
    """创建溢价率差值图（优化交互）"""
    
    etf_codes = list(data.keys())
    
    if len(etf_codes) < 2:
        return None
    
    # 创建子图
    fig = make_subplots(
        rows=len(etf_codes)-1, 
        cols=1,
        subplot_titles=[f'{etf_codes[0]} vs {code}' for code in etf_codes[1:]],
        vertical_spacing=0.08
    )
    
    colors = ['#e74c3c', '#3498db', '#2ecc71', '#f39c12', '#9b59b6']
    
    df_base = data[etf_codes[0]]
    
    for i, code in enumerate(etf_codes[1:], 1):
        df_compare = data[code]
        
        # 合并数据
        merged = pd.merge(
            df_base[['日期', '溢价率', '收盘', '净值']], 
            df_compare[['日期', '溢价率', '收盘', '净值']], 
            on='日期', 
            suffixes=(f'_{etf_codes[0]}', f'_{code}')
        )
        
        if len(merged) > 0:
            # 计算差值
            spread = merged[f'溢价率_{etf_codes[0]}'] - merged[f'溢价率_{code}']
            
            # 添加差值线
            fig.add_trace(go.Scatter(
                x=merged['日期'],
                y=spread,
                mode='lines',
                name=f'{etf_codes[0]} vs {code}',
                line=dict(color=colors[(i-1) % len(colors)], width=2),
                hovertemplate=(
                    f'<b>{etf_codes[0]} vs {code}</b><br>' +
                    '日期: %{x|%Y-%m-%d}<br>' +
                    f'{etf_codes[0]}: ' + '%{customdata[0]:.2f}%<br>' +
                    f'{code}: ' + '%{customdata[1]:.2f}%<br>' +
                    '差值: %{y:.2f}%<br>' +
                    '<extra></extra>'
                ),
                customdata=merged[[f'溢价率_{etf_codes[0]}', f'溢价率_{code}']].values
            ), row=i, col=1)
            
            # 标记套利机会
            mask_above = spread >= threshold
            mask_below = spread <= -threshold
            mask = mask_above | mask_below
            
            if mask.any():
                fig.add_trace(go.Scatter(
                    x=merged.loc[mask, '日期'],
                    y=spread[mask],
                    mode='markers',
                    name='套利机会' if i == 1 else None,
                    marker=dict(color='red', size=10, symbol='circle'),
                    showlegend=True if i == 1 else False,
                    hovertemplate=(
                        f'<b>套利机会!</b><br>' +
                        '日期: %{x|%Y-%m-%d}<br>' +
                        '差值: %{y:.2f}%<br>' +
                        '<extra></extra>'
                    )
                ), row=i, col=1)
            
            # 添加阈值线
            fig.add_hline(y=threshold, line_dash="dash", line_color="red", 
                         opacity=0.7, row=i, col=1)
            fig.add_hline(y=-threshold, line_dash="dash", line_color="green",
                         opacity=0.7, row=i, col=1)
            fig.add_hline(y=0, line_dash="solid", line_color="gray",
                         opacity=0.5, row=i, col=1)
            
            # y轴配置
            fig.update_yaxes(
                tickformat='.1f',
                gridcolor='rgba(0,0,0,0.1)',
                zerolinecolor='rgba(0,0,0,0.3)',
                row=i, col=1
            )
        
        # 添加阈值线
        fig.add_hline(y=threshold, line_dash="dash", line_color="red", 
                     opacity=0.7, row=i, col=1)
        fig.add_hline(y=-threshold, line_dash="dash", line_color="green",
                     opacity=0.7, row=i, col=1)
        fig.add_hline(y=0, line_dash="solid", line_color="gray",
                     opacity=0.5, row=i, col=1)
        
        # y轴配置
        fig.update_yaxes(
            tickformat='.1f',
            gridcolor='rgba(0,0,0,0.1)',
            zerolinecolor='rgba(0,0,0,0.3)',
            row=i, col=1
        )
        
        # x轴配置
        fig.update_xaxes(
            type="date",
            tickformat='%Y-%m-%d',
            tickfont=dict(size=10),
            gridcolor='rgba(0,0,0,0.1)',
            row=i, col=1
        )
    
    fig.update_layout(
        title={
            'text': title,
            'x': 0.5,
            'xanchor': 'center',
            'font': dict(size=18)
        },
        height=300 * (len(etf_codes)-1) + 100,
        hovermode='x unified',
        template='plotly_white',
        showlegend=True,
        dragmode='pan',
        legend=dict(
            orientation="h",
            yanchor="bottom",
            y=1.02,
            xanchor="right",
            x=1
        ),
        hoverlabel=dict(
            bgcolor="white",
            font_size=12
        )
    )
    
    return fig


def create_distribution_chart(data, title="ETF溢价率分布"):
    """创建溢价率分布图（优化交互）"""
    
    fig = go.Figure()
    colors = ['#1f77b4', '#ff7f0e', '#2ca02c', '#d62728', '#9467bd', '#8c564b']
    
    for i, (code, df) in enumerate(data.items()):
        fig.add_trace(go.Histogram(
            x=df['溢价率'],
            name=code,
            opacity=0.6,
            marker_color=colors[i % len(colors)],
            nbinsx=30,
            hovertemplate=(
                f'<b>{code}</b><br>' +
                '溢价率: %{x:.2f}%<br>' +
                '频次: %{y}<br>' +
                '<extra></extra>'
            )
        ))
    
    fig.add_vline(x=0, line_dash="dash", line_color="gray", opacity=0.5)
    
    fig.update_layout(
        title={
            'text': title,
            'x': 0.5,
            'xanchor': 'center',
            'font': dict(size=18)
        },
        xaxis_title='溢价率 (%)',
        yaxis_title='频次',
        barmode='overlay',
        template='plotly_white',
        height=500,
        dragmode='pan',
        legend=dict(
            orientation="h",
            yanchor="bottom",
            y=1.02,
            xanchor="right",
            x=1
        ),
        xaxis=dict(
            tickformat='.1f',
            gridcolor='rgba(0,0,0,0.1)'
        ),
        yaxis=dict(
            gridcolor='rgba(0,0,0,0.1)'
        ),
        hoverlabel=dict(
            bgcolor="white",
            font_size=12
        )
    )
    
    return fig


def create_summary_stats(data, threshold=2.0):
    """创建统计汇总"""
    
    etf_codes = list(data.keys())
    stats = []
    
    for i in range(len(etf_codes)):
        for j in range(i+1, len(etf_codes)):
            etf1, etf2 = etf_codes[i], etf_codes[j]
            
            merged = pd.merge(
                data[etf1][['日期', '溢价率']].rename(columns={'溢价率': f'溢价率_{etf1}'}),
                data[etf2][['日期', '溢价率']].rename(columns={'溢价率': f'溢价率_{etf2}'}),
                on='日期'
            )
            
            spread = merged[f'溢价率_{etf1}'] - merged[f'溢价率_{etf2}']
            
            stats.append({
                'ETF对': f'{etf1}-{etf2}',
                '最大正差值': f'{spread.max():.2f}%',
                '最大负差值': f'{spread.min():.2f}%',
                '平均差值': f'{spread.mean():.2f}%',
                '标准差': f'{spread.std():.2f}%',
                '套利机会数': f'{(spread.abs() >= threshold).sum()}',
                '机会频率': f'{(spread.abs() >= threshold).mean()*100:.1f}%'
            })
    
    return pd.DataFrame(stats)


def generate_html():
    """生成完整的HTML报告"""
    
    print("生成交互式HTML报告...")
    print("-" * 60)
    
    # 加载配置
    config = load_config()
    
    if config:
        etf_codes = config.get('etf_codes', [])
        chart_title = config.get('name', 'ETF套利分析')
        threshold = config.get('threshold', 2.0)
    else:
        etf_codes = ['513100', '159941', '159501', '159659']
        chart_title = 'ETF套利分析'
        threshold = 2.0
    
    # 加载数据
    data = load_data(etf_codes)
    if not data:
        print("错误：未找到数据文件，请先运行 etf_arbitrage.py")
        return
    
    print(f"加载数据: {len(data)} 只ETF")
    
    # 创建图表
    print("1. 生成溢价率对比图...")
    fig1 = create_premium_chart(data, title="溢价率走势")
    
    print("2. 生成跟踪误差对比图...")
    tracking_data = load_tracking_error_data(etf_codes)
    if tracking_data:
        index_name = config.get('benchmark', '指数') if config else '指数'
        fig_te = create_tracking_error_chart(tracking_data, index_name=index_name, title=f"ETF跟踪误差走势（相对于{index_name}）")
        print(f"   加载跟踪误差数据: {len(tracking_data)} 只ETF")
        
        # 生成ETF与指数走势对比图
        print("   生成ETF与指数走势对比图...")
        fig_etf_index = create_etf_vs_index_chart(tracking_data, index_name=index_name, title=f"ETF与{index_name}累计收益对比")
        
        # 计算R²
        r_squared_data = calculate_r_squared_data(etf_codes)
        if r_squared_data:
            print(f"   跟踪精度计算完成: {len(r_squared_data)} 只ETF")
    else:
        fig_te = None
        fig_etf_index = None
        r_squared_data = []
        print("   警告: 未找到跟踪误差数据")
    
    print("3. 生成所有ETF对溢价率差值图...")
    spread_charts = create_all_spread_charts(data, threshold=threshold, chart_title="ETF对")
    
    print("4. 生成溢价率分布图...")
    fig3 = create_distribution_chart(data, title="溢价率分布")
    
    print("4. 生成统计汇总...")
    stats_df = create_summary_stats(data, threshold)
    
    # 保存图表
    output_dir = Path("data")
    output_dir.mkdir(exist_ok=True)
    
    # 生成图表HTML（用于嵌入到主报告）
    fig1_html = fig1.to_html(
        full_html=False,
        include_plotlyjs='cdn',
        config=dict(
            scrollZoom=True,
            displayModeBar=True,
            displaylogo=False,
            modeBarButtonsToAdd=['pan2d', 'zoomIn2d', 'zoomOut2d', 'autoScale2d', 'resetScale2d']
        )
    )
    print(f"   ✓ chart_premium_trend.html")
    
    # 生成跟踪误差图表HTML
    if fig_te:
        fig_te_html = fig_te.to_html(
            full_html=False,
            include_plotlyjs=False,
            config=dict(
                scrollZoom=True,
                displayModeBar=True,
                displaylogo=False,
                modeBarButtonsToAdd=['pan2d', 'zoomIn2d', 'zoomOut2d', 'autoScale2d', 'resetScale2d']
            )
        )
        print(f"   ✓ chart_tracking_error.html")
    else:
        fig_te_html = None
    
    # 生成ETF与指数走势对比图HTML
    if fig_etf_index:
        fig_etf_index_html = fig_etf_index.to_html(
            full_html=False,
            include_plotlyjs=False,
            config=dict(
                scrollZoom=True,
                displayModeBar=True,
                displaylogo=False,
                modeBarButtonsToAdd=['pan2d', 'zoomIn2d', 'zoomOut2d', 'autoScale2d', 'resetScale2d']
            )
        )
        print(f"   ✓ chart_etf_vs_index.html")
    else:
        fig_etf_index_html = None
    
    # 为每个差值图表生成HTML
    spread_charts_html = []
    for chart in spread_charts:
        chart_html = chart['fig'].to_html(
            full_html=False,
            include_plotlyjs=False,
            config=dict(
                scrollZoom=True,
                displayModeBar=True,
                displaylogo=False,
                modeBarButtonsToAdd=['pan2d', 'zoomIn2d', 'zoomOut2d', 'autoScale2d', 'resetScale2d']
            )
        )
        spread_charts_html.append({
            'title': chart['title'],
            'html': chart_html
        })
        print(f"   ✓ {chart['filename']}")
    
    fig3_html = fig3.to_html(
        full_html=False,
        include_plotlyjs=False,
        config=dict(
            scrollZoom=True,
            displayModeBar=True,
            displaylogo=False,
            modeBarButtonsToAdd=['pan2d', 'zoomIn2d', 'zoomOut2d', 'autoScale2d', 'resetScale2d']
        )
    )
    print(f"   ✓ chart_distribution.html")
    
    # 保存统计数据
    if stats_df is not None and len(stats_df) > 0:
        stats_df.to_csv(output_dir / "arbitrage_stats.csv", index=False)
        print(f"   ✓ arbitrage_stats.csv")
    
    # 生成表格行（用于排序功能）
    table_rows = ''
    if stats_df is not None and len(stats_df) > 0:
        for _, row in stats_df.iterrows():
            table_rows += f"<tr><td><b>{row['ETF对']}</b></td><td class='positive' data-value='{row['最大正差值']}'>{row['最大正差值']}</td><td class='negative' data-value='{row['最大负差值']}'>{row['最大负差值']}</td><td data-value='{row['平均差值']}'>{row['平均差值']}</td><td data-value='{row['标准差']}'>{row['标准差']}</td><td data-value='{row['套利机会数']}'>{row['套利机会数']}</td><td data-value='{row['机会频率']}'>{row['机会频率']}</td></tr>"
    
    # 生成完整的分析报告
    html_content = f"""
<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <title>{chart_title}</title>
    <style>
        * {{
            box-sizing: border-box;
        }}
        body {{
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Arial, sans-serif;
            max-width: 1400px;
            margin: 0 auto;
            padding: 20px;
            background-color: #f5f5f5;
            color: #333;
        }}
        h1 {{
            color: #1a1a1a;
            text-align: center;
            border-bottom: 3px solid #1f77b4;
            padding-bottom: 15px;
            margin-bottom: 25px;
        }}
        .info {{
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            padding: 20px;
            border-radius: 10px;
            margin: 20px 0;
            box-shadow: 0 4px 6px rgba(0,0,0,0.1);
        }}
        .info h3 {{
            margin-top: 0;
            color: white;
        }}
        .info ul {{
            margin-bottom: 0;
            padding-left: 20px;
        }}
        .info li {{
            margin: 5px 0;
        }}
        .chart-container {{
            background-color: white;
            padding: 20px;
            margin: 25px 0;
            border-radius: 10px;
            box-shadow: 0 2px 10px rgba(0,0,0,0.1);
        }}
        .chart-title {{
            font-size: 20px;
            font-weight: bold;
            margin-bottom: 15px;
            color: #1a1a1a;
            display: flex;
            align-items: center;
            justify-content: space-between;
        }}
        .chart-hint {{
            font-size: 12px;
            color: #666;
            font-weight: normal;
            background: #f0f0f0;
            padding: 5px 12px;
            border-radius: 15px;
        }}
        .stats-table {{
            width: 100%;
            border-collapse: collapse;
            margin: 20px 0;
            font-size: 14px;
        }}
        .stats-table th, .stats-table td {{
            border: 1px solid #ddd;
            padding: 12px 8px;
            text-align: center;
        }}
        .stats-table th {{
            background: linear-gradient(135deg, #1f77b4 0%, #0d5a8f 100%);
            color: white;
            font-weight: 600;
        }}
        .stats-table tr:nth-child(even) {{
            background-color: #f8f9fa;
        }}
        .stats-table tr:hover {{
            background-color: #e8f4f8;
        }}
        .positive {{ color: #e74c3c; font-weight: bold; }}
        .negative {{ color: #27ae60; font-weight: bold; }}
        .footer {{
            text-align: center;
            margin-top: 30px;
            padding: 20px;
            color: #666;
            font-size: 13px;
        }}
        .interaction-tips {{
            background-color: #fff3cd;
            border: 1px solid #ffc107;
            border-radius: 8px;
            padding: 15px;
            margin: 15px 0;
            font-size: 13px;
        }}
        .interaction-tips h4 {{
            margin: 0 0 10px 0;
            color: #856404;
        }}
        .interaction-tips ul {{
            margin: 0;
            padding-left: 20px;
            color: #856404;
        }}
        .interaction-tips li {{
            margin: 3px 0;
        }}
        iframe {{
            width: 100%;
            border: none;
            border-radius: 8px;
        }}
    </style>
</head>
<body>
    <h1>{chart_title}</h1>
    
    <div class="info">
        <h3>📊 分析概览</h3>
        <ul>
            <li><strong>分析时间:</strong> {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</li>
            <li><strong>ETF数量:</strong> {len(data)} 只</li>
            <li><strong>套利阈值:</strong> ±{threshold}%</li>
        </ul>
    </div>
    
    <div class="chart-container">
        <div class="chart-title">
            📈 溢价率走势
            <span class="chart-hint">🎯 可缩放、可拖拽、可悬停</span>
        </div>
        <div class="interaction-tips">
            <h4>💡 交互提示</h4>
            <ul>
                <li><strong>缩放:</strong> 鼠标滚轮 或 点击图表上方的"📈 缩放"按钮</li>
                <li><strong>平移:</strong> 按住鼠标拖拽 或 点击"✋ 平移"按钮</li>
                <li><strong>重置:</strong> 点击"🔍 重置"按钮恢复初始视图</li>
                <li><strong>悬停:</strong> 鼠标移动到曲线上查看详细数据</li>
                <li><strong>范围滑块:</strong> 图表底部有缩放滑块，可快速调整时间范围</li>
            </ul>
        </div>
        {fig1_html}
    </div>
    
    {f'''<div class="chart-container">
        <div class="chart-title">
            📉 ETF跟踪误差走势
            <span class="chart-hint">🎯 相对于{config.get('benchmark', '指数') if config else '指数'}</span>
        </div>
        <div class="interaction-tips">
            <h4>💡 跟踪误差说明</h4>
            <ul>
                <li><strong>跟踪误差:</strong> ETF净值涨幅 - 指数涨跌幅</li>
                <li><strong>零线:</strong> 表示完美跟踪</li>
                <li><strong>正值:</strong> ETF净值涨幅超过指数</li>
                <li><strong>负值:</strong> ETF净值涨幅落后指数</li>
            </ul>
        </div>
        <div class="chart-container" style="margin: 15px 0; padding: 15px; background: #f8f9fa;">
            <div class="chart-title" style="font-size: 16px;">📊 跟踪精度排名</div>
            <table class="stats-table" style="margin: 10px 0;">
                <tr>
                    <th>排名</th>
                    <th>ETF代码</th>
                    <th>跟踪精度</th>
                </tr>
                {''.join([f"<tr><td><b>{i+1}</b></td><td><b>{code}</b></td><td>{r2*100:.2f}%</td></tr>" for i, (code, r2) in enumerate(r_squared_data)])}
            </table>
        </div>
        {fig_te_html}
        
        <div class="chart-container" style="margin-top: 30px;">
            <div class="chart-title" style="font-size: 16px;">
                📈 ETF与指数累计收益对比
                <span class="chart-hint">🎯 从起始日归一化，0%=起点</span>
            </div>
            <div class="interaction-tips">
                <h4>💡 累计收益说明</h4>
                <ul>
                    <li><strong>归一化:</strong> 起始日设为0%，显示累计涨跌</li>
                    <li><strong>实线:</strong> 各ETF净值累计收益率</li>
                    <li><strong>虚线:</strong> 基准指数累计收益率</li>
                    <li><strong>对比:</strong> 线与线越接近，表示跟踪越精准</li>
                </ul>
            </div>
            {fig_etf_index_html if fig_etf_index_html else '<p style="color: #999; text-align: center;">暂无数据</p>'}
        </div>
    </div>''' if fig_te_html else ''}
    
    <div class="chart-container">
        <div class="chart-title">
            📊 溢价率差值走势
            <span class="chart-hint">🎯 包含所有ETF配对对比</span>
        </div>
        {''.join([f'''<div class="chart-container">
            <div class="chart-title" style="font-size: 16px;">📊 {chart['title']}</div>
            {chart['html']}
        </div>''' for chart in spread_charts_html])}
    </div>
    
    <div class="chart-container">
        <div class="chart-title">
            📉 溢价率分布
            <span class="chart-hint">🎯 可缩放、可拖拽</span>
        </div>
        {fig3_html}
    </div>
    
    <div class="chart-container">
        <div class="chart-title">📋 套利机会统计 <span style="font-size: 12px; color: #666; font-weight: normal;">(点击表头排序)</span></div>
        <table class="stats-table" id="arbitrage-table">
            <thead>
                <tr>
                    <th onclick="sortTable(0)" style="cursor: pointer;">ETF对 ↕</th>
                    <th onclick="sortTable(1)" style="cursor: pointer;">最大正差值 ↕</th>
                    <th onclick="sortTable(2)" style="cursor: pointer;">最大负差值 ↕</th>
                    <th onclick="sortTable(3)" style="cursor: pointer;">平均差值 ↕</th>
                    <th onclick="sortTable(4)" style="cursor: pointer;">标准差 ↕</th>
                    <th onclick="sortTable(5)" style="cursor: pointer;">套利机会数 ↕</th>
                    <th onclick="sortTable(6)" style="cursor: pointer;">机会频率 ↕</th>
                </tr>
            </thead>
            <tbody>
                {table_rows}
            </tbody>
        </table>
    </div>
    
    <script src="sort-table.js"></script>
    
    <div class="footer">
        <p>Generated by ETF Arbitrage Analysis Tool</p>
        <p>💡 提示: 使用浏览器Ctrl+滚轮可全局缩放页面</p>
    </div>
</body>
</html>
"""
    
    # 保存主报告
    main_report = output_dir / "report.html"
    with open(main_report, 'w', encoding='utf-8') as f:
        f.write(html_content)
    
    print(f"\n   ✓ {main_report} (主报告)")
    print("-" * 60)
    
    print(f"\n🎉 完成！请在浏览器中打开:")
    print(f"   {main_report.absolute()}")
    print(f"\n💡 优化内容:")
    print(f"   ✓ 滚轮缩放已启用")
    print(f"   ✓ 拖拽平移已启用")
    print(f"   ✓ 底部范围滑块")
    print(f"   ✓ 图表上方交互按钮（缩放/平移/重置）")


if __name__ == "__main__":
    generate_html()
