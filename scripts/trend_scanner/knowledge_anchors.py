"""
知识锚点体系 — Phase 3: FinClaw 知识锚点整合

将 FinClaw 的 references/ 知识锚点编码为可进化的因子种子+验证规则。
每个知识锚点包含：
- 维度: 分析方向（趋势/动量/波动率/成交量等）
- 核心逻辑: 为什么有效
- 因子种子: 可供 LLM 生成的因子表达式
- 验证规则: 该因子应满足的 IC/IR/胜率阈值
- 适用市场: 哪些品种/周期适用
- 来源: 研报/论文/策略

使用方式:
    from trend_scanner.knowledge_anchors import KnowledgeAnchorManager

    mgr = KnowledgeAnchorManager(db_path="data/meta.db")
    anchors = mgr.get_anchors_by_dimension("momentum")
    seed = mgr.get_factor_seed("momentum_rsi_divergence")
"""

import json
import logging
from dataclasses import dataclass, field, asdict
from typing import Optional, List, Dict, Any
from datetime import datetime
import sqlite3

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# 知识锚点数据结构
# ---------------------------------------------------------------------------

@dataclass
class KnowledgeAnchor:
    """知识锚点 — 将分析方法论编码为可验证的因子种子"""
    anchor_id: str                    # 唯一标识，如 "momentum_rsi_divergence"
    dimension: str                    # 分析维度: momentum/trend/volatility/volume/basis/seasonality/macro
    title: str                        # 人类可读标题
    core_logic: str                   # 核心逻辑（为什么有效）
    factor_seeds: List[Dict[str, Any]]  # 因子种子列表: [{expression, name, description}]
    validation_rules: Dict[str, Any]   # 验证规则: {min_ic, min_ir, min_win_rate, max_drawdown}
    applicable_markets: List[str]      # 适用市场: ["black", "energy", "agriculture", "all"]
    applicable_timeframes: List[str]   # 适用周期: ["daily", "1h", "all"]
    source: str                        # 来源: 研报/论文/策略
    source_url: str = ""               # 来源链接
    confidence: float = 0.5            # 置信度 (0-1)
    usage_count: int = 0               # 使用次数
    win_rate_observed: float = 0.0     # 实际观测胜率
    created_at: str = ""
    updated_at: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


# ---------------------------------------------------------------------------
# 默认知识锚点库（核心种子）
# ---------------------------------------------------------------------------

DEFAULT_ANCHORS = [
    # ===== 动量维度 =====
    {
        "anchor_id": "momentum_rsi_extreme",
        "dimension": "momentum",
        "title": "RSI极值反转",
        "core_logic": "RSI进入超买/超卖区域后，价格存在均值回归倾向。极端RSI值往往预示短期反转。"
        "但需结合趋势强度判断：强趋势中RSI可长期钝化。",
        "factor_seeds": [
            {"expression": "rsi_14 < 25", "name": "rsi_oversold", "description": "RSI<25，超卖信号"},
            {"expression": "rsi_14 > 75", "name": "rsi_overbought", "description": "RSI>75，超买信号"},
            {"expression": "rsi_14 * (1 - trend_strength)", "name": "rsi_trend_adjusted",
             "description": "RSI经趋势强度调整，趋势越强RSI信号越弱"},
        ],
        "validation_rules": {"min_ic": 0.02, "min_ir": 0.3, "min_win_rate": 0.45, "max_drawdown": 15},
        "applicable_markets": ["all"],
        "applicable_timeframes": ["daily", "1h"],
        "source": "经典技术分析",
        "confidence": 0.6,
    },
    {
        "anchor_id": "momentum_tsi_divergence",
        "dimension": "momentum",
        "title": "TSI背离",
        "core_logic": "TSI(Trend Strength Index)与价格背离，预示趋势动能衰竭。"
        "TSI持续为负但价格创新低→底背离，反之顶背离。",
        "factor_seeds": [
            {"expression": "tsi - tsi.shift(5)", "name": "tsi_momentum",
             "description": "TSI 5日变化率，衡量动量加速度"},
            {"expression": "tsi * er", "name": "tsi_efficiency",
             "description": "TSI与效率比率乘积，兼顾动量和趋势效率"},
        ],
        "validation_rules": {"min_ic": 0.03, "min_ir": 0.4, "min_win_rate": 0.48, "max_drawdown": 12},
        "applicable_markets": ["all"],
        "applicable_timeframes": ["daily"],
        "source": "自研指标",
        "confidence": 0.7,
    },
    {
        "anchor_id": "momentum_macd_histogram",
        "dimension": "momentum",
        "title": "MACD柱状图动量",
        "core_logic": "MACD柱状图由负转正/由正转负，是动量反转的领先信号。"
        "柱状图斜率加速表示趋势增强。",
        "factor_seeds": [
            {"expression": "macd_hist", "name": "macd_hist_raw", "description": "MACD柱状图原始值"},
            {"expression": "macd_hist - macd_hist.shift(1)", "name": "macd_hist_accel",
             "description": "MACD柱状图加速度，正值表示多头加速"},
        ],
        "validation_rules": {"min_ic": 0.025, "min_ir": 0.35, "min_win_rate": 0.46, "max_drawdown": 14},
        "applicable_markets": ["all"],
        "applicable_timeframes": ["daily", "1h"],
        "source": "经典技术分析",
        "confidence": 0.55,
    },

    # ===== 趋势维度 =====
    {
        "anchor_id": "trend_efficiency_ratio",
        "dimension": "trend",
        "title": "效率比率(ER)趋势强度",
        "core_logic": "ER = |净价格变化| / |逐根K线价格变化之和|。"
        "ER>0.6表示趋势效率高，ER<0.3表示震荡。"
        "ER是趋势跟踪策略的核心过滤器。",
        "factor_seeds": [
            {"expression": "er", "name": "er_raw", "description": "效率比率原始值"},
            {"expression": "er * r_squared", "name": "er_r2_composite",
             "description": "ER与R²乘积，双重确认趋势强度"},
        ],
        "validation_rules": {"min_ic": 0.04, "min_ir": 0.5, "min_win_rate": 0.50, "max_drawdown": 10},
        "applicable_markets": ["all"],
        "applicable_timeframes": ["daily"],
        "source": "Kaufman效率比率",
        "confidence": 0.8,
    },
    {
        "anchor_id": "trend_hurst_exponent",
        "dimension": "trend",
        "title": "Hurst指数趋势持续性",
        "core_logic": "H>0.5趋势持续，H<0.5均值回归，H≈0.5随机游走。"
        "Hurst指数是判断趋势持续性的数学基础。",
        "factor_seeds": [
            {"expression": "hurst", "name": "hurst_raw", "description": "Hurst指数原始值"},
            {"expression": "hurst - 0.5", "name": "hurst_deviation",
             "description": "Hurst偏离0.5的程度，正值表示趋势持续"},
        ],
        "validation_rules": {"min_ic": 0.03, "min_ir": 0.4, "min_win_rate": 0.48, "max_drawdown": 12},
        "applicable_markets": ["all"],
        "applicable_timeframes": ["daily"],
        "source": "Hurst指数理论",
        "confidence": 0.65,
    },
    {
        "anchor_id": "trend_composite_strength",
        "dimension": "trend",
        "title": "复合趋势强度",
        "core_logic": "综合ER、R²、TSI、ADX、Hurst等指标构建复合趋势强度评分。"
        "多指标共识比单一指标更可靠。",
        "factor_seeds": [
            {"expression": "trend_strength_composite", "name": "trend_composite",
             "description": "复合趋势强度，综合多维度趋势指标"},
        ],
        "validation_rules": {"min_ic": 0.05, "min_ir": 0.6, "min_win_rate": 0.52, "max_drawdown": 8},
        "applicable_markets": ["all"],
        "applicable_timeframes": ["daily"],
        "source": "自研复合指标",
        "confidence": 0.85,
    },

    # ===== 波动率维度 =====
    {
        "anchor_id": "volatility_atr_breakout",
        "dimension": "volatility",
        "title": "ATR突破",
        "core_logic": "价格突破ATR通道（如±2ATR），是趋势启动信号。"
        "ATR扩张伴随价格突破→新趋势启动；ATR收缩→盘整蓄势。",
        "factor_seeds": [
            {"expression": "(close - ma20) / atr_14", "name": "price_atr_ratio",
             "description": "价格偏离均线的ATR归一化值"},
            {"expression": "atr_14 / atr_14.shift(20) - 1", "name": "atr_expansion",
             "description": "ATR扩张率，正值表示波动放大"},
        ],
        "validation_rules": {"min_ic": 0.03, "min_ir": 0.4, "min_win_rate": 0.47, "max_drawdown": 13},
        "applicable_markets": ["all"],
        "applicable_timeframes": ["daily", "1h"],
        "source": "ATR理论",
        "confidence": 0.7,
    },
    {
        "anchor_id": "volatility_bollinger_squeeze",
        "dimension": "volatility",
        "title": "布林带收窄",
        "core_logic": "布林带带宽收窄至历史低位，预示波动率即将爆发。"
        "带宽 = (上轨-下轨)/中轨，带宽<20%为收窄。",
        "factor_seeds": [
            {"expression": "(bb_upper - bb_lower) / bb_middle", "name": "bb_bandwidth",
             "description": "布林带带宽"},
            {"expression": "1 - (bb_upper - bb_lower) / (bb_upper - bb_lower).rolling(60).rank(pct=True)",
             "name": "bb_squeeze_score", "description": "布林带收窄评分，1=最窄"},
        ],
        "validation_rules": {"min_ic": 0.02, "min_ir": 0.3, "min_win_rate": 0.45, "max_drawdown": 15},
        "applicable_markets": ["all"],
        "applicable_timeframes": ["daily"],
        "source": "布林带理论",
        "confidence": 0.6,
    },

    # ===== 成交量维度 =====
    {
        "anchor_id": "volume_obv_divergence",
        "dimension": "volume",
        "title": "OBV背离",
        "core_logic": "OBV(On-Balance Volume)与价格背离，预示趋势即将反转。"
        "价涨量跌→顶背离；价跌量涨→底背离。",
        "factor_seeds": [
            {"expression": "obv", "name": "obv_raw", "description": "OBV原始值"},
            {"expression": "obv / obv.rolling(20).mean() - 1", "name": "obv_deviation",
             "description": "OBV相对20日均值的偏离"},
        ],
        "validation_rules": {"min_ic": 0.02, "min_ir": 0.3, "min_win_rate": 0.46, "max_drawdown": 14},
        "applicable_markets": ["all"],
        "applicable_timeframes": ["daily"],
        "source": "经典技术分析",
        "confidence": 0.5,
    },
    {
        "anchor_id": "volume_mfi_extreme",
        "dimension": "volume",
        "title": "MFI极值",
        "core_logic": "MFI(Money Flow Index)是成交量加权的RSI。"
        "MFI>80表示资金大量流入（可能过热），MFI<20表示资金流出（可能超卖）。",
        "factor_seeds": [
            {"expression": "mfi", "name": "mfi_raw", "description": "MFI原始值"},
            {"expression": "mfi - 50", "name": "mfi_deviation", "description": "MFI偏离中值"},
        ],
        "validation_rules": {"min_ic": 0.02, "min_ir": 0.3, "min_win_rate": 0.45, "max_drawdown": 15},
        "applicable_markets": ["all"],
        "applicable_timeframes": ["daily"],
        "source": "经典技术分析",
        "confidence": 0.5,
    },

    # ===== 基差维度（FinClaw 新增） =====
    {
        "anchor_id": "basis_contango_backwardation",
        "dimension": "basis",
        "title": "基差升贴水结构",
        "core_logic": "正基差(现货>期货)为Backwardation，反映现货偏紧/看涨预期。"
        "负基差(现货<期货)为Contango，反映库存充足/看跌预期。"
        "基差收敛/扩大可作为套利信号。",
        "factor_seeds": [
            {"expression": "basis_rate", "name": "basis_rate_raw", "description": "基差率(%)"},
            {"expression": "basis_rate * (1 - abs(basis_rate)/10)", "name": "basis_adjusted",
             "description": "基差率经幅度调整，极值信号弱化"},
        ],
        "validation_rules": {"min_ic": 0.02, "min_ir": 0.3, "min_win_rate": 0.45, "max_drawdown": 15},
        "applicable_markets": ["all"],
        "applicable_timeframes": ["daily"],
        "source": "FinClaw基差分析",
        "confidence": 0.55,
    },

    # ===== 季节性维度（FinClaw 新增） =====
    {
        "anchor_id": "seasonality_monthly_pattern",
        "dimension": "seasonality",
        "title": "月度季节性规律",
        "core_logic": "某些月份具有统计显著的涨跌倾向。"
        "如黑色系9-10月需求旺季，农产品1月供需报告窗口。"
        "季节性是辅助维度，需结合当前供需格局判断。",
        "factor_seeds": [
            {"expression": "current_month_signal", "name": "seasonal_signal",
             "description": "当前月份的历史平均涨跌幅"},
            {"expression": "current_month_pos_rate - 50", "name": "seasonal_bias",
             "description": "当前月份上涨概率偏离50%的程度"},
        ],
        "validation_rules": {"min_ic": 0.01, "min_ir": 0.2, "min_win_rate": 0.43, "max_drawdown": 18},
        "applicable_markets": ["all"],
        "applicable_timeframes": ["daily"],
        "source": "FinClaw季节性分析",
        "confidence": 0.4,
    },

    # ===== 可见图维度（论文启发） =====
    {
        "anchor_id": "vgrsi_visibility_rsi",
        "dimension": "momentum",
        "title": "可见图RSI(VGRSI)",
        "core_logic": "将时间序列转换为可见图网络，利用价格点之间的几何可见关系"
        "替代传统RSI的简单价格变化。VGRSI对趋势拐点的识别更敏感。",
        "factor_seeds": [
            {"expression": "vgrsi_a0", "name": "vgrsi_mean", "description": "VGRSI均值聚合(A0)"},
            {"expression": "vgrsi_a1", "name": "vgrsi_ratio", "description": "VGRSI比率聚合(A1)"},
        ],
        "validation_rules": {"min_ic": 0.03, "min_ir": 0.4, "min_win_rate": 0.48, "max_drawdown": 12},
        "applicable_markets": ["all"],
        "applicable_timeframes": ["daily"],
        "source": "arXiv:2605.01300",
        "confidence": 0.6,
    },
]


# ---------------------------------------------------------------------------
# KnowledgeAnchorManager
# ---------------------------------------------------------------------------

class KnowledgeAnchorManager:
    """知识锚点管理器

    职责：
    - 存储/检索/更新知识锚点
    - 为 LLM 因子生成器提供种子
    - 跟踪锚点使用效果
    - 智能推荐锚点
    """

    def __init__(self, db_path: str = "data/meta.db"):
        self._db_path = db_path
        self._init_db()

    def _init_db(self):
        """初始化 SQLite 表"""
        try:
            conn = sqlite3.connect(self._db_path)
            cursor = conn.cursor()

            cursor.execute("""
                CREATE TABLE IF NOT EXISTS knowledge_anchors (
                    anchor_id TEXT PRIMARY KEY,
                    dimension TEXT NOT NULL,
                    title TEXT NOT NULL,
                    core_logic TEXT,
                    factor_seeds TEXT,  -- JSON
                    validation_rules TEXT,  -- JSON
                    applicable_markets TEXT,  -- JSON
                    applicable_timeframes TEXT,  -- JSON
                    source TEXT,
                    source_url TEXT DEFAULT '',
                    confidence REAL DEFAULT 0.5,
                    usage_count INTEGER DEFAULT 0,
                    win_rate_observed REAL DEFAULT 0.0,
                    created_at TEXT,
                    updated_at TEXT
                )
            """)

            conn.commit()
            conn.close()

        except Exception as e:
            logger.warning(f"初始化知识锚点表失败: {e}")

    def _row_to_anchor(self, row: tuple) -> KnowledgeAnchor:
        """将数据库行转换为 KnowledgeAnchor"""
        return KnowledgeAnchor(
            anchor_id=row[0], dimension=row[1], title=row[2],
            core_logic=row[3],
            factor_seeds=json.loads(row[4]) if row[4] else [],
            validation_rules=json.loads(row[5]) if row[5] else {},
            applicable_markets=json.loads(row[6]) if row[6] else ["all"],
            applicable_timeframes=json.loads(row[7]) if row[7] else ["daily"],
            source=row[8] or "", source_url=row[9] or "",
            confidence=row[10] or 0.5, usage_count=row[11] or 0,
            win_rate_observed=row[12] or 0.0,
            created_at=row[13] or "", updated_at=row[14] or "",
        )

    def seed_default_anchors(self) -> int:
        """导入默认知识锚点库

        返回:
            新增锚点数
        """
        count = 0
        for data in DEFAULT_ANCHORS:
            if not self.get_anchor(data["anchor_id"]):
                self.save_anchor(KnowledgeAnchor(
                    anchor_id=data["anchor_id"],
                    dimension=data["dimension"],
                    title=data["title"],
                    core_logic=data["core_logic"],
                    factor_seeds=data.get("factor_seeds", []),
                    validation_rules=data.get("validation_rules", {}),
                    applicable_markets=data.get("applicable_markets", ["all"]),
                    applicable_timeframes=data.get("applicable_timeframes", ["daily"]),
                    source=data.get("source", ""),
                    confidence=data.get("confidence", 0.5),
                    created_at=datetime.now().isoformat(),
                    updated_at=datetime.now().isoformat(),
                ))
                count += 1
        return count

    def save_anchor(self, anchor: KnowledgeAnchor) -> bool:
        """保存知识锚点（upsert）"""
        try:
            conn = sqlite3.connect(self._db_path)
            cursor = conn.cursor()

            cursor.execute("""
                INSERT OR REPLACE INTO knowledge_anchors
                (anchor_id, dimension, title, core_logic, factor_seeds,
                 validation_rules, applicable_markets, applicable_timeframes,
                 source, source_url, confidence, usage_count, win_rate_observed,
                 created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                anchor.anchor_id, anchor.dimension, anchor.title,
                anchor.core_logic,
                json.dumps(anchor.factor_seeds, ensure_ascii=False),
                json.dumps(anchor.validation_rules, ensure_ascii=False),
                json.dumps(anchor.applicable_markets, ensure_ascii=False),
                json.dumps(anchor.applicable_timeframes, ensure_ascii=False),
                anchor.source, anchor.source_url, anchor.confidence,
                anchor.usage_count, anchor.win_rate_observed,
                anchor.created_at, anchor.updated_at,
            ))

            conn.commit()
            conn.close()
            return True

        except Exception as e:
            logger.error(f"保存知识锚点失败({anchor.anchor_id}): {e}")
            return False

    def get_anchor(self, anchor_id: str) -> Optional[KnowledgeAnchor]:
        """获取单个知识锚点"""
        try:
            conn = sqlite3.connect(self._db_path)
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM knowledge_anchors WHERE anchor_id = ?", (anchor_id,))
            row = cursor.fetchone()
            conn.close()
            return self._row_to_anchor(row) if row else None
        except Exception:
            return None

    def get_anchors_by_dimension(self, dimension: str) -> List[KnowledgeAnchor]:
        """按维度获取锚点列表"""
        try:
            conn = sqlite3.connect(self._db_path)
            cursor = conn.cursor()
            cursor.execute(
                "SELECT * FROM knowledge_anchors WHERE dimension = ? ORDER BY confidence DESC",
                (dimension,)
            )
            rows = cursor.fetchall()
            conn.close()
            return [self._row_to_anchor(row) for row in rows]
        except Exception:
            return []

    def get_all_anchors(self) -> List[KnowledgeAnchor]:
        """获取所有锚点"""
        try:
            conn = sqlite3.connect(self._db_path)
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM knowledge_anchors ORDER BY confidence DESC")
            rows = cursor.fetchall()
            conn.close()
            return [self._row_to_anchor(row) for row in rows]
        except Exception:
            return []

    def get_factor_seeds_for_llm(self, dimension: str = None, market: str = None) -> List[Dict]:
        """为 LLM 因子生成器提供种子

        参数:
            dimension: 指定维度（None=全部）
            market: 指定市场（None=全部）

        返回:
            [{anchor_id, dimension, title, core_logic, factor_seeds, validation_rules}]
        """
        anchors = self.get_all_anchors()
        seeds = []

        for anchor in anchors:
            if dimension and anchor.dimension != dimension:
                continue
            if market and market not in anchor.applicable_markets and "all" not in anchor.applicable_markets:
                continue
            if anchor.factor_seeds:
                seeds.append({
                    "anchor_id": anchor.anchor_id,
                    "dimension": anchor.dimension,
                    "title": anchor.title,
                    "core_logic": anchor.core_logic,
                    "factor_seeds": anchor.factor_seeds,
                    "validation_rules": anchor.validation_rules,
                    "confidence": anchor.confidence,
                })

        return seeds

    def update_usage(self, anchor_id: str, win_rate: float = None):
        """更新锚点使用统计"""
        try:
            conn = sqlite3.connect(self._db_path)
            cursor = conn.cursor()

            if win_rate is not None:
                cursor.execute("""
                    UPDATE knowledge_anchors
                    SET usage_count = usage_count + 1,
                        win_rate_observed = ?,
                        updated_at = ?
                    WHERE anchor_id = ?
                """, (win_rate, datetime.now().isoformat(), anchor_id))
            else:
                cursor.execute("""
                    UPDATE knowledge_anchors
                    SET usage_count = usage_count + 1,
                        updated_at = ?
                    WHERE anchor_id = ?
                """, (datetime.now().isoformat(), anchor_id))

            conn.commit()
            conn.close()
        except Exception as e:
            logger.debug(f"更新锚点使用统计失败({anchor_id}): {e}")

    def get_statistics(self) -> Dict[str, Any]:
        """获取锚点统计"""
        try:
            conn = sqlite3.connect(self._db_path)
            cursor = conn.cursor()

            cursor.execute("SELECT COUNT(*) FROM knowledge_anchors")
            total = cursor.fetchone()[0]

            cursor.execute("SELECT dimension, COUNT(*) FROM knowledge_anchors GROUP BY dimension")
            by_dimension = dict(cursor.fetchall())

            cursor.execute("SELECT AVG(confidence) FROM knowledge_anchors")
            avg_confidence = cursor.fetchone()[0] or 0

            cursor.execute("SELECT SUM(usage_count) FROM knowledge_anchors")
            total_usage = cursor.fetchone()[0] or 0

            conn.close()

            return {
                "total_anchors": total,
                "by_dimension": by_dimension,
                "avg_confidence": round(avg_confidence, 2),
                "total_usage": total_usage,
            }
        except Exception:
            return {}
