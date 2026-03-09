"""
ETF套利分析 - MVP版本
使用AKShare获取真实历史净值数据
包含跟踪误差分析功能
"""

import akshare as ak
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import argparse
import json
from pathlib import Path

# 基准指数配置映射表
BENCHMARK_CONFIGS = {
    # 美股指数 - 使用 index_us_stock_sina
    "纳斯达克": {"data_source": "us_stock", "symbol": ".NDX", "name": "纳斯达克100"},
    "标普": {"data_source": "us_stock", "symbol": ".INX", "name": "标普500"},
    
    # 亚洲指数 - 使用 index_global_hist_sina
    "日经": {"data_source": "global_hist", "symbol": "日经225指数", "name": "日经225"},
}

def parse_benchmark(benchmark_name):
    """
    解析基准指数名称，返回配置
    
    Args:
        benchmark_name: 用户配置的基准指数名称
        
    Returns:
        dict: 包含 name, data_source, symbol 的配置字典
    """
    if not benchmark_name:
        # 默认使用纳斯达克
        return BENCHMARK_CONFIGS["纳斯达克"].copy()
    
    # 精确匹配
    if benchmark_name in BENCHMARK_CONFIGS:
        return BENCHMARK_CONFIGS[benchmark_name].copy()
    
    # 模糊匹配
    benchmark_lower = benchmark_name.lower()
    for key, config in BENCHMARK_CONFIGS.items():
        if key.lower() in benchmark_lower or benchmark_lower in key.lower():
            print(f"  注意: 将 '{benchmark_name}' 匹配为 '{key}'")
            return config.copy()
    
    # 未匹配到，使用默认
    print(f"  警告: 未找到 '{benchmark_name}' 的配置，使用默认纳斯达克")
    return BENCHMARK_CONFIGS["纳斯达克"].copy()

class ETFCacheManager:
    """ETF数据缓存管理器"""
    
    def __init__(self, cache_dir="data/cache"):
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        
    def load(self, name):
        """加载缓存"""
        cache_path = self.cache_dir / f"{name}.csv"
        if cache_path.exists():
            df = pd.read_csv(cache_path)
            if '日期' in df.columns:
                df['日期'] = pd.to_datetime(df['日期'])
            if '净值日期' in df.columns:
                df['净值日期'] = pd.to_datetime(df['净值日期'])
            return df
        return None
    
    def save(self, name, df):
        """保存缓存"""
        cache_path = self.cache_dir / f"{name}.csv"
        df.to_csv(cache_path, index=False)


class GlobalIndexFetcher:
    """全球指数数据获取器（支持配置化数据源）"""
    
    def __init__(self, benchmark_name=None, cache_dir="data/cache"):
        """
        初始化
        
        Args:
            benchmark_name: 基准指数名称（如"纳斯达克100"、"日经225"等）
        """
        self.cache = ETFCacheManager(cache_dir)
        # 解析benchmark配置
        self.index_config = parse_benchmark(benchmark_name)
        self.index_name = self.index_config['name']
        self.data_source = self.index_config['data_source']
        self.symbol = self.index_config['symbol']
        self.cache_key = f"index_{self.index_name}"
    
    def _fetch_from_us_stock(self):
        """从美股接口获取数据"""
        return ak.index_us_stock_sina(symbol=self.symbol)
    
    def _fetch_from_global_hist(self):
        """从全球历史接口获取数据"""
        return ak.index_global_hist_sina(symbol=self.symbol)
    
    def get_index_data(self, start_date=None, end_date=None):
        """
        获取指数历史数据
        
        Returns:
            DataFrame with columns: 日期, 开盘, 收盘, 最高, 最低, 涨跌幅
        """
        print(f"\n获取{self.index_name}指数数据...")
        
        # 加载缓存
        cached = self.cache.load(self.cache_key)
        
        # 如果没有指定日期范围，直接返回缓存
        if start_date is None and end_date is None:
            if cached is not None:
                print(f"  使用完整缓存 ({len(cached)}条)", end=" ")
                return cached
            # 无缓存且无日期范围，请求最近365天
            start_date = (datetime.now() - timedelta(days=365)).strftime('%Y-%m-%d')
            end_date = datetime.now().strftime('%Y-%m-%d')
        elif start_date is None:
            start_date = (datetime.now() - timedelta(days=365)).strftime('%Y-%m-%d')
        elif end_date is None:
            end_date = datetime.now().strftime('%Y-%m-%d')
        
        # 转换日期
        query_start = pd.to_datetime(start_date)
        query_end = pd.to_datetime(end_date)
        
        # 如果有缓存，确定需要补充的数据范围
        if cached is not None and len(cached) > 0:
            cache_start = cached['日期'].min()
            cache_end = cached['日期'].max()
            
            # 如果查询范围完全在缓存范围内，直接过滤返回
            if query_start >= cache_start and query_end <= cache_end:
                filtered = cached[(cached['日期'] >= query_start) & (cached['日期'] <= query_end)]
                print(f"  使用缓存 ({len(filtered)}条)", end=" ")
                return filtered
            
            # 需要补充数据
            need_fetch = False
            fetch_start = query_start
            fetch_end = query_end
            
            if query_start < cache_start:
                need_fetch = True
            if query_end > cache_end:
                need_fetch = True
            
            if need_fetch:
                print(f"  本地缓存: {cache_start.strftime('%Y-%m-%d')}至{cache_end.strftime('%Y-%m-%d')}, 需补充: {query_start.strftime('%Y-%m-%d')}至{query_end.strftime('%Y-%m-%d')}", end=" ")
                fetch_start = min(query_start, cache_start)
                fetch_end = max(query_end, cache_end)
            else:
                filtered = cached[(cached['日期'] >= query_start) & (cached['日期'] <= query_end)]
                print(f"  使用缓存 ({len(filtered)}条)", end=" ")
                return filtered
        else:
            fetch_start = query_start
            fetch_end = query_end
            print(f"  无缓存，请求数据...", end=" ")
        
        # 根据数据源选择不同的接口
        try:
            if self.data_source == 'us_stock':
                df = self._fetch_from_us_stock()
            elif self.data_source == 'global_hist':
                df = self._fetch_from_global_hist()
            else:
                raise ValueError(f"不支持的数据源: {self.data_source}")
            
            if df is not None and len(df) > 0:
                # 统一列名（不同接口返回的列名可能略有不同）
                df = df.rename(columns={
                    'date': '日期',
                    'open': '开盘',
                    'high': '最高',
                    'low': '最低',
                    'close': '收盘',
                    'volume': '成交量'
                })
                
                # 确保日期列存在且格式正确
                if '日期' in df.columns:
                    df['日期'] = pd.to_datetime(df['日期'])
                
                # 只保留需要的列
                required_cols = ['日期', '开盘', '收盘', '最高', '最低']
                available_cols = [col for col in required_cols if col in df.columns]
                df = df[available_cols].copy()
                df = df.sort_values('日期').reset_index(drop=True)
                
                # 计算涨跌幅
                df['涨跌幅'] = df['收盘'].pct_change() * 100
                
                # 合并缓存数据
                if cached is not None and len(cached) > 0:
                    df = pd.concat([cached, df], ignore_index=True)
                    df = df.drop_duplicates(subset=['日期'], keep='last')
                    df = df.sort_values('日期').reset_index(drop=True)
                    print(f"合并完成 ({len(df)}条)", end=" ")
                
                # 保存缓存
                self.cache.save(self.cache_key, df)
                
                # 返回查询范围内的数据
                result = df[(df['日期'] >= query_start) & (df['日期'] <= query_end)]
                print(f"✓ ({len(result)}条)")
                return result
                
        except Exception as e:
            print(f"失败: {e}")
        
        # 请求失败，如果有缓存，返回缓存中查询范围内的数据
        if cached is not None and len(cached) > 0:
            filtered = cached[(cached['日期'] >= query_start) & (cached['日期'] <= query_end)]
            if len(filtered) > 0:
                print(f"  使用缓存数据 ({len(filtered)}条)", end=" ")
                return filtered
        
        return None


class ETFDataFetcher:
    """ETF数据获取器"""
    
    def __init__(self, cache_dir="data/cache"):
        self.cache = ETFCacheManager(cache_dir)
    
    def get_etf_data(self, etf_code, start_date=None, end_date=None, expected_days=None):
        """
        获取ETF的完整数据（价格+净值）
        
        Args:
            etf_code: ETF代码
            start_date: 开始日期
            end_date: 结束日期
            expected_days: 期望的数据条数，不足则重新请求
        
        Returns:
            DataFrame with columns: 日期, 收盘, 净值, 溢价率
        """
        print(f"\n获取ETF {etf_code} 数据...")
        
        # 1. 获取价格数据（历史行情）
        print(f"  获取价格数据...", end=" ")
        price_df = self._get_price_data(etf_code, start_date, end_date)
        if price_df is None or len(price_df) == 0:
            print(f"失败")
            return None
        print(f"✓ ({len(price_df)}条)")
        
        # 2. 获取净值数据
        print(f"  获取净值数据...", end=" ")
        nav_df = self._get_nav_data(etf_code, start_date, end_date)
        if nav_df is None or len(nav_df) == 0:
            print(f"失败")
            return None
        print(f"✓ ({len(nav_df)}条)")
        
        # 3. 合并数据（按日期对齐）
        merged = self._merge_data(price_df, nav_df)
        if merged is None or len(merged) == 0:
            print(f"  合并数据失败")
            return None
        
        print(f"  合并后: {len(merged)}条数据 ({merged['日期'].min().strftime('%Y-%m-%d')} 至 {merged['日期'].max().strftime('%Y-%m-%d')})")
        
        return merged
    
    def _get_price_data(self, etf_code, start_date=None, end_date=None):
        """
        获取ETF历史价格数据（使用东方财富接口，支持增量更新）
        """
        cache_key = f"price_{etf_code}"
        
        # 加载缓存
        cached = self.cache.load(cache_key)
        
        # 如果没有指定日期范围，直接返回缓存
        if start_date is None and end_date is None:
            if cached is not None:
                print(f"使用完整缓存 ({len(cached)}条)", end=" ")
                return cached
            # 无缓存且无日期范围，请求最近365天
            start_date = (datetime.now() - timedelta(days=365)).strftime('%Y-%m-%d')
            end_date = datetime.now().strftime('%Y-%m-%d')
        elif start_date is None:
            start_date = (datetime.now() - timedelta(days=365)).strftime('%Y-%m-%d')
        elif end_date is None:
            end_date = datetime.now().strftime('%Y-%m-%d')
        
        # 转换日期
        query_start = pd.to_datetime(start_date)
        query_end = pd.to_datetime(end_date)
        
        # 如果有缓存，确定需要补充的数据范围
        if cached is not None and len(cached) > 0:
            cache_start = cached['日期'].min()
            cache_end = cached['日期'].max()
            
            # 如果查询范围完全在缓存范围内，直接过滤返回
            if query_start >= cache_start and query_end <= cache_end:
                filtered = cached[(cached['日期'] >= query_start) & (cached['日期'] <= query_end)]
                print(f"使用缓存 ({len(filtered)}条，缓存范围: {cache_start.strftime('%Y-%m-%d')}至{cache_end.strftime('%Y-%m-%d')})", end=" ")
                return filtered
            
            # 需要补充数据
            need_fetch = False
            fetch_start = query_start
            fetch_end = query_end
            
            if query_start < cache_start:
                # 需要获取缓存之前的数据
                need_fetch = True
            if query_end > cache_end:
                # 需要获取缓存之后的数据
                need_fetch = True
            
            if need_fetch:
                print(f"本地缓存: {cache_start.strftime('%Y-%m-%d')}至{cache_end.strftime('%Y-%m-%d')}, 需补充: {query_start.strftime('%Y-%m-%d')}至{query_end.strftime('%Y-%m-%d')}", end=" ")
                
                # 合并查询范围
                fetch_start = min(query_start, cache_start)
                fetch_end = max(query_end, cache_end)
            else:
                # 只需在缓存范围内过滤
                filtered = cached[(cached['日期'] >= query_start) & (cached['日期'] <= query_end)]
                print(f"使用缓存 ({len(filtered)}条)", end=" ")
                return filtered
        else:
            # 无缓存，需要请求全部数据
            fetch_start = query_start
            fetch_end = query_end
            print(f"无缓存，请求数据...", end=" ")
        
        # 从东方财富接口获取
        try:
            df = ak.fund_etf_hist_em(
                symbol=etf_code,
                period="daily",
                start_date=fetch_start.strftime('%Y%m%d'),
                end_date=fetch_end.strftime('%Y%m%d'),
                adjust=""
            )
            
            if df is not None and len(df) > 0:
                # 转换列名
                df.columns = ['日期', '开盘', '收盘', '最高', '最低', '成交量', '成交额', '振幅', '涨跌幅', '涨跌额', '换手率']
                df['日期'] = pd.to_datetime(df['日期'])
                
                # 合并缓存数据
                if cached is not None and len(cached) > 0:
                    # 合并新旧数据
                    df = pd.concat([cached, df], ignore_index=True)
                    # 去重
                    df = df.drop_duplicates(subset=['日期'], keep='last')
                    # 排序
                    df = df.sort_values('日期').reset_index(drop=True)
                    print(f"合并完成 ({len(df)}条)", end=" ")
                
                # 保存缓存
                self.cache.save(cache_key, df)
                
                # 返回查询范围内的数据
                result = df[(df['日期'] >= query_start) & (df['日期'] <= query_end)]
                return result
                
        except Exception as e:
            print(f"失败: {e}")
        
        # 请求失败，如果有缓存，返回缓存中查询范围内的数据
        if cached is not None and len(cached) > 0:
            filtered = cached[(cached['日期'] >= query_start) & (cached['日期'] <= query_end)]
            if len(filtered) > 0:
                print(f"使用缓存数据 ({len(filtered)}条)", end=" ")
                return filtered
        
        return None
    
    def _get_nav_data(self, etf_code, start_date=None, end_date=None):
        """获取ETF历史净值数据（带重试）"""
        cache_key = f"nav_{etf_code}"
        
        # 检查缓存
        cached = self.cache.load(cache_key)
        if cached is not None:
            # 根据日期过滤
            if start_date:
                cached = cached[cached['净值日期'] >= pd.to_datetime(start_date)]
            if end_date:
                cached = cached[cached['净值日期'] <= pd.to_datetime(end_date)]
            if len(cached) > 0:
                print(f"使用缓存数据 ({len(cached)}条)", end=" ")
                return cached
        
        # 从AKShare获取（带重试）
        import time
        for attempt in range(3):
            try:
                df = ak.fund_open_fund_info_em(
                    symbol=etf_code,
                    indicator='单位净值走势',
                    period='成立来'
                )
                
                if df is not None and len(df) > 0:
                    df['净值日期'] = pd.to_datetime(df['净值日期'])
                    # 保存缓存
                    self.cache.save(cache_key, df)
                    return df
                    
            except Exception as e:
                if attempt < 2:
                    print(f"重试{attempt+1}...", end=" ")
                    time.sleep(1)
                else:
                    print(f"失败: {e}")
        
        return None
    
    def _merge_data(self, price_df, nav_df):
        """合并价格和净值数据"""
        # 重命名列以便合并
        price_df = price_df[['日期', '收盘']].copy()
        nav_df = nav_df[['净值日期', '单位净值']].copy()
        nav_df.columns = ['日期', '净值']
        
        # 按日期合并
        merged = pd.merge(price_df, nav_df, on='日期', how='inner')
        
        if len(merged) == 0:
            return None
        
        # 计算溢价率
        merged['溢价率'] = ((merged['收盘'] - merged['净值']) / merged['净值']) * 100
        
        return merged.sort_values('日期').reset_index(drop=True)
    
    def calculate_tracking_error(self, etf_df, index_df):
        """
        计算ETF相对于纳斯达克指数的跟踪误差（使用净值涨幅）
        
        Args:
            etf_df: ETF数据 DataFrame (包含 日期, 净值, 收盘)
            index_df: 纳斯达克指数数据 DataFrame (包含 日期, 收盘, 涨跌幅)
        
        Returns:
            DataFrame with columns: 日期, ETF净值涨幅, 指数涨跌幅, 跟踪误差
        """
        # 准备数据（使用净值计算涨幅）
        etf = etf_df[['日期', '净值']].copy()
        etf['ETF净值涨幅'] = etf['净值'].pct_change() * 100
        
        index = index_df[['日期', '收盘', '涨跌幅']].copy()
        index = index.rename(columns={'涨跌幅': '指数涨跌幅'})
        
        # 合并数据
        merged = pd.merge(etf, index, on='日期', how='inner')
        
        if len(merged) == 0:
            return None
        
        # 计算跟踪误差 = ETF净值涨幅 - 指数涨跌幅
        merged['跟踪误差'] = merged['ETF净值涨幅'] - merged['指数涨跌幅']
        
        return merged.sort_values('日期').reset_index(drop=True)
    
    def calculate_r_squared(self, etf_df, index_df):
        """
        计算ETF跟踪指数的决定系数R²
        
        Args:
            etf_df: ETF数据 DataFrame (包含 日期, 净值)
            index_df: 纳斯达克指数数据 DataFrame (包含 日期, 涨跌幅)
        
        Returns:
            float: R²值（0-1之间）
        """
        # 准备数据
        etf = etf_df[['日期', '净值']].copy()
        etf['ETF净值涨幅'] = etf['净值'].pct_change() * 100
        
        index = index_df[['日期', '涨跌幅']].copy()
        index = index.rename(columns={'涨跌幅': '指数涨跌幅'})
        
        # 合并数据
        merged = pd.merge(etf, index, on='日期', how='inner')
        
        if len(merged) < 2:
            return None
        
        # 删除NaN
        merged = merged.dropna()
        
        if len(merged) < 2:
            return None
        
        # 计算R²（使用numpy数组）
        y = np.array(merged['ETF净值涨幅'])
        x = np.array(merged['指数涨跌幅'])
        
        # 计算相关系数
        correlation = np.corrcoef(x, y)[0, 1]
        r_squared = correlation ** 2
        
        return r_squared


def analyze_arbitrage_opportunities(data_dict, threshold=2.0):
    """分析套利机会"""
    etf_codes = list(data_dict.keys())
    
    print(f"\n{'='*70}")
    print(f"套利机会分析（阈值: ±{threshold}%）")
    print(f"{'='*70}")
    
    total_opportunities = 0
    all_results = []
    
    for i in range(len(etf_codes)):
        for j in range(i+1, len(etf_codes)):
            etf1, etf2 = etf_codes[i], etf_codes[j]
            
            # 对齐数据
            df1 = data_dict[etf1][['日期', '溢价率']].copy()
            df2 = data_dict[etf2][['日期', '溢价率']].copy()
            df2.columns = ['日期', '溢价率_2']
            
            merged = pd.merge(df1, df2, on='日期', how='inner')
            
            if len(merged) == 0:
                continue
            
            # 计算差值
            spread = merged['溢价率'] - merged['溢价率_2']
            
            # 统计
            opportunities = (abs(spread) >= threshold).sum()
            max_spread = spread.abs().max()
            min_spread = spread.min()
            max_positive = spread.max()
            avg_spread = spread.abs().mean()
            
            total_opportunities += opportunities
            
            result = {
                'ETF对': f"{etf1}-{etf2}",
                '共同交易日': len(merged),
                '套利机会': opportunities,
                '机会占比': f"{opportunities/len(merged)*100:.1f}%",
                '最大正差值': f"{max_positive:.2f}%",
                '最大负差值': f"{min_spread:.2f}%",
                '最大绝对差值': f"{max_spread:.2f}%",
                '平均绝对差值': f"{avg_spread:.2f}%",
            }
            all_results.append(result)
            
            print(f"\n{etf1} vs {etf2}:")
            print(f"  共同交易日: {len(merged)}天")
            print(f"  套利机会: {opportunities}次 ({opportunities/len(merged)*100:.1f}%)")
            print(f"  最大正差值: {max_positive:+.2f}%")
            print(f"  最大负差值: {min_spread:.2f}%")
            print(f"  平均绝对差值: {avg_spread:.2f}%")
    
    return total_opportunities, all_results


def print_summary(data_dict, total_opportunities, all_results):
    """打印汇总"""
    print(f"\n{'='*70}")
    print("分析汇总")
    print(f"{'='*70}")
    
    # 单个ETF统计
    print(f"\n单只ETF溢价率统计:")
    for code, df in data_dict.items():
        avg = df['溢价率'].mean()
        max_p = df['溢价率'].max()
        min_p = df['溢价率'].min()
        std = df['溢价率'].std()
        print(f"  {code}: 平均{avg:+.2f}% | 最高{max_p:+.2f}% | 最低{min_p:+.2f}% | 波动{std:.2f}%")
    
    # 套利机会汇总
    if all_results:
        max_spread = max([float(r['最大绝对差值'].replace('%','')) for r in all_results])
        best_pair = max(all_results, key=lambda x: float(x['最大绝对差值'].replace('%','')))
        
        print(f"\n套利机会汇总:")
        print(f"  总套利机会: {total_opportunities}次")
        print(f"  最佳套利对: {best_pair['ETF对']} (最大差值 {best_pair['最大绝对差值']})")
        print(f"  历史最大溢价率差值: {max_spread:.2f}%")
        
        # 可行性评估
        print(f"\n可行性评估:")
        if max_spread > 5:
            print(f"  ✓ 套利空间充足，历史上出现过大幅溢价差异，策略可行！")
        elif max_spread > 3:
            print(f"  △ 有一定套利空间，但机会相对较少")
        else:
            print(f"  ✗ 套利空间有限，需谨慎评估")
        
        # 风险提示
        print(f"\n风险提示:")
        print(f"  1. 溢价率差值回归可能需要时间，存在持仓风险")
        print(f"  2. 需考虑交易成本（佣金+滑点，约0.1-0.3%）")
        print(f"  3. 建议在差值>3%时操作，预留足够安全边际")
        print(f"  4. 先用小资金测试策略有效性")


def load_config():
    """加载配置文件"""
    config_path = Path("config.json")
    if config_path.exists():
        with open(config_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    return None


def main():
    """主函数"""
    # 加载配置
    config = load_config()
    
    # 解析命令行参数
    parser = argparse.ArgumentParser(description='ETF套利分析工具')
    parser.add_argument('--days', '-d', type=int, help='最近N天，默认90天')
    parser.add_argument('--start', '-s', type=str, help='开始日期 (YYYY-MM-DD)')
    parser.add_argument('--end', '-e', type=str, help='结束日期 (YYYY-MM-DD)，默认今天')
    parser.add_argument('--threshold', '-t', type=float, help='套利阈值 (%%)', default=2.0)
    args = parser.parse_args()
    
    # 获取配置
    if config:
        ETF_CODES = config.get('etf_codes', [])
        THRESHOLD = args.threshold if args.threshold != 2.0 else config.get('threshold', 2.0)
        DEFAULT_DAYS = config.get('default_days', 90)
        PROJECT_NAME = config.get('name', 'ETF套利分析')
    else:
        ETF_CODES = ['513100', '159941', '159501', '159659']
        THRESHOLD = args.threshold
        DEFAULT_DAYS = 90
        PROJECT_NAME = 'ETF套利分析'
    
    print("="*70)
    print(PROJECT_NAME)
    print("="*70)
    print(f"运行时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
    
    # 计算日期范围
    END_DATE = datetime.now()
    
    if args.days:
        START_DATE = END_DATE - timedelta(days=args.days)
    elif args.start:
        START_DATE = datetime.strptime(args.start, '%Y-%m-%d')
    else:
        START_DATE = END_DATE - timedelta(days=DEFAULT_DAYS)
    
    if args.end:
        END_DATE = datetime.strptime(args.end, '%Y-%m-%d')
    
    START_DATE_STR = START_DATE.strftime('%Y-%m-%d')
    END_DATE_STR = END_DATE.strftime('%Y-%m-%d')
    
    expected_days = (END_DATE - START_DATE).days
    
    print(f"配置:")
    print(f"  ETF: {', '.join(ETF_CODES)}")
    print(f"  时间范围: {START_DATE_STR} 至 {END_DATE_STR} (约{expected_days}天)")
    print(f"  套利阈值: ±{THRESHOLD}%")
    print(f"  数据缓存: data/cache/")
    
    # 获取数据
    fetcher = ETFDataFetcher()
    data_dict = {}
    
    for code in ETF_CODES:
        df = fetcher.get_etf_data(
            etf_code=code,
            start_date=START_DATE.strftime('%Y-%m-%d'),
            end_date=END_DATE.strftime('%Y-%m-%d'),
            expected_days=expected_days
        )
        if df is not None and len(df) > 0:
            data_dict[code] = df
    
    if len(data_dict) < 2:
        print(f"\n错误: 仅获取到 {len(data_dict)} 只ETF数据，无法进行对比分析")
        return
    
    print(f"\n{'='*70}")
    print(f"成功获取 {len(data_dict)} 只ETF数据，开始分析...")
    
    # 保存结果到CSV（提前定义output_dir）
    output_dir = Path("data")
    output_dir.mkdir(exist_ok=True)
    
    # 获取指数数据（根据配置）
    print(f"\n{'='*70}")
    benchmark = config.get('benchmark', '纳斯达克100') if config else '纳斯达克100'
    print(f"获取{benchmark}数据...")
    index_fetcher = GlobalIndexFetcher(benchmark)
    index_df = index_fetcher.get_index_data(
        start_date=START_DATE.strftime('%Y-%m-%d'),
        end_date=END_DATE.strftime('%Y-%m-%d')
    )
    
    if index_df is not None and len(index_df) > 0:
        print(f"  {benchmark}数据: {len(index_df)}条 ({index_df['日期'].min().strftime('%Y-%m-%d')} 至 {index_df['日期'].max().strftime('%Y-%m-%d')})")
        
        # 计算每个ETF的跟踪误差
        print(f"\n计算ETF跟踪误差...")
        tracking_error_dict = {}
        r_squared_dict = {}
        
        print(f"\n跟踪误差统计:")
        for code, df in data_dict.items():
            te_df = fetcher.calculate_tracking_error(df, index_df)
            if te_df is not None and len(te_df) > 0:
                tracking_error_dict[code] = te_df
                
                # 计算R²
                r2 = fetcher.calculate_r_squared(df, index_df)
                if r2 is not None:
                    r_squared_dict[code] = r2
                
                print(f"  {code}: {len(te_df)}条数据 | 平均跟踪误差: {te_df['跟踪误差'].abs().mean():.2f}% | 跟踪精度: {r2*100:.2f}%" if r2 else f"  {code}: {len(te_df)}条数据")
        
        # 按R²排序显示
        if r_squared_dict:
            print(f"\n跟踪表现排名（跟踪精度，越高越好）:")
            sorted_r2 = sorted(r_squared_dict.items(), key=lambda x: x[1], reverse=True)
            for i, (code, r2) in enumerate(sorted_r2, 1):
                print(f"  {i}. {code}: {r2*100:.2f}%")
        
        # 保存跟踪误差数据
        for code, df in tracking_error_dict.items():
            output_file = output_dir / f"{code}_tracking_error.csv"
            df.to_csv(output_file, index=False)
    else:
        print(f"  警告: 无法获取纳斯达克指数数据")
        tracking_error_dict = {}
    
    # 分析套利机会
    total_opportunities, all_results = analyze_arbitrage_opportunities(data_dict, THRESHOLD)
    
    # 打印汇总
    print_summary(data_dict, total_opportunities, all_results)
    
    # 保存结果到CSV
    # 保存每只ETF的溢价率数据
    for code, df in data_dict.items():
        output_file = output_dir / f"{code}_premium.csv"
        df.to_csv(output_file, index=False)
    
    # 保存套利机会统计
    if all_results:
        stats_df = pd.DataFrame(all_results)
        stats_file = output_dir / "arbitrage_stats.csv"
        stats_df.to_csv(stats_file, index=False)
    
    # 保存跟踪误差数据
    if tracking_error_dict:
        for code, df in tracking_error_dict.items():
            output_file = output_dir / f"{code}_tracking_error.csv"
            df.to_csv(output_file, index=False)
    
    print(f"\n结果已保存到:")
    print(f"  - data/*_premium.csv (每只ETF的溢价率数据)")
    print(f"  - data/*_tracking_error.csv (每只ETF的跟踪误差数据)")
    if all_results:
        print(f"  - data/arbitrage_stats.csv (套利统计)")
    
    print(f"\n{'='*70}")
    print("分析完成！")
    print(f"{'='*70}")


if __name__ == "__main__":
    main()
