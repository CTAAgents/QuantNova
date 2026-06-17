"""
地缘政治事件追踪模块

追踪和评估地缘政治风险，支持：
- 战争/冲突风险
- 制裁风险
- 关税/贸易战风险
- 领土争端风险
- 和平协议/外交突破

使用方式：
    from fundamental.geopolitical import GeopoliticalTracker
    
    tracker = GeopoliticalTracker()
    risks = tracker.track(symbol="SC")
"""

import json
import logging
import os
import re
import sys
from datetime import datetime, timedelta
from typing import Any

import requests

# 导入数据模型
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
from trend_scanner.models import GeopoliticalRisk

logger = logging.getLogger(__name__)


class GeopoliticalTracker:
    """
    地缘政治风险追踪器
    
    追踪和评估地缘政治风险对期货市场的影响。
    """
    
    # 地区与品种的关联
    REGION_SYMBOL_MAP = {
        # 中东地区
        "中东": {
            "affected_commodities": ["energy", "precious"],
            "affected_symbols": ["SC", "FU", "BU", "LU", "AU", "AG"],
            "description": "中东是全球主要的能源产区，地缘政治风险直接影响原油供应",
        },
        # 俄罗斯/乌克兰
        "俄罗斯": {
            "affected_commodities": ["energy", "agricultural", "nonferrous"],
            "affected_symbols": ["SC", "AU", "CU", "AL", "NI"],
            "description": "俄罗斯是重要的能源和金属出口国",
        },
        # 中国
        "中国": {
            "affected_commodities": ["ferrous", "nonferrous", "agricultural"],
            "affected_symbols": ["RB", "HC", "I", "CU", "AL", "M", "Y"],
            "description": "中国是全球最大的大宗商品消费国",
        },
        # 美国
        "美国": {
            "affected_commodities": ["energy", "agricultural", "precious"],
            "affected_symbols": ["SC", "AU", "AG", "M", "Y", "C"],
            "description": "美国是重要的能源生产国和农产品出口国",
        },
        # 南海
        "南海": {
            "affected_commodities": ["energy"],
            "affected_symbols": ["SC", "FU", "LU"],
            "description": "南海是重要的航运通道，影响能源运输",
        },
    }
    
    # 风险类型与影响
    RISK_TYPE_IMPACT = {
        "war": {
            "default_level": "high",
            "description": "战争/军事冲突",
            "impact": "供应中断风险，避险情绪上升",
        },
        "sanctions": {
            "default_level": "medium",
            "description": "经济制裁",
            "impact": "贸易受限，供应减少",
        },
        "tariffs": {
            "default_level": "medium",
            "description": "关税/贸易战",
            "impact": "贸易成本上升，需求下降",
        },
        "dispute": {
            "default_level": "low",
            "description": "领土/外交争端",
            "impact": "市场不确定性增加",
        },
        "peace_agreement": {
            "default_level": "low",
            "description": "和平协议/外交突破",
            "impact": "风险溢价消退，供应恢复预期",
        },
    }
    
    # 关键词与风险类型映射
    KEYWORD_RISK_TYPE = {
        # 战争/冲突
        "战争": "war", "军事": "war", "冲突": "war", "攻击": "war",
        "导弹": "war", "空袭": "war", "轰炸": "war", "入侵": "war",
        # 制裁
        "制裁": "sanctions", "禁运": "sanctions", "封锁": "sanctions",
        "冻结资产": "sanctions", "黑名单": "sanctions",
        # 关税
        "关税": "tariffs", "贸易战": "tariffs", "加征关税": "tariffs",
        "贸易摩擦": "tariffs", "贸易壁垒": "tariffs",
        # 争端
        "争端": "dispute", "领土": "dispute", "领海": "dispute",
        "主权": "dispute", "外交": "dispute",
        # 和平
        "和平": "peace_agreement", "协议": "peace_agreement",
        "谈判": "peace_agreement", "停火": "peace_agreement",
        "和解": "peace_agreement", "外交突破": "peace_agreement",
    }
    
    # 地区关键词
    REGION_KEYWORDS = {
        "中东": ["中东", "伊朗", "伊拉克", "沙特", "以色列", "叙利亚", "也门", "黎巴嫩"],
        "俄罗斯": ["俄罗斯", "乌克兰", "俄乌", "克里米亚", "顿巴斯"],
        "中国": ["中国", "南海", "台海", "台湾", "香港"],
        "美国": ["美国", "美联储", "华盛顿", "白宫"],
        "南海": ["南海", "南沙", "西沙", "钓鱼岛"],
    }
    
    def __init__(self, cache_dir: str = None):
        """
        初始化地缘政治风险追踪器
        
        Args:
            cache_dir: 缓存目录
        """
        # 缓存目录
        self.cache_dir = cache_dir or os.path.join(
            os.path.dirname(os.path.abspath(__file__)), "..", "..", "data", "geopolitical_cache"
        )
        os.makedirs(self.cache_dir, exist_ok=True)
        
        # 缓存有效期（小时）
        self.cache_hours = 12
        
        # 已知的风险事件（从缓存加载）
        self.known_risks = self._load_known_risks()
    
    def _load_known_risks(self) -> list[dict]:
        """加载已知的风险事件"""
        cache_path = os.path.join(self.cache_dir, "known_risks.json")
        if os.path.exists(cache_path):
            try:
                with open(cache_path, encoding="utf-8") as f:
                    return json.load(f)
            except Exception:
                pass
        return []
    
    def _save_known_risks(self):
        """保存已知的风险事件"""
        cache_path = os.path.join(self.cache_dir, "known_risks.json")
        try:
            with open(cache_path, "w", encoding="utf-8") as f:
                json.dump(self.known_risks, f, ensure_ascii=False, indent=2)
        except Exception as e:
            logger.warning(f"保存已知风险事件失败: {e}")
    
    def track(self, symbol: str = None, region: str = None) -> list[GeopoliticalRisk]:
        """
        追踪地缘政治风险
        
        Args:
            symbol: 品种代码（可选）
            region: 地区（可选）
            
        Returns:
            地缘政治风险列表
        """
        logger.info(f"追踪地缘政治风险，品种：{symbol}，地区：{region}")
        
        risks = []
        
        # 根据品种确定关注地区
        if symbol:
            regions = self._get_regions_for_symbol(symbol)
        elif region:
            regions = [region]
        else:
            regions = list(self.REGION_SYMBOL_MAP.keys())
        
        # 从已知风险事件中筛选
        for risk_data in self.known_risks:
            risk_region = risk_data.get("region", "")
            risk_symbols = risk_data.get("affected_symbols", [])
            
            # 检查是否相关
            if risk_region in regions or (symbol and symbol in risk_symbols):
                risk = self._create_risk_from_data(risk_data)
                if risk:
                    risks.append(risk)
        
        # 按风险等级排序
        risk_order = {"high": 0, "medium": 1, "low": 2}
        risks.sort(key=lambda x: risk_order.get(x.risk_level, 3))
        
        logger.info(f"找到{len(risks)}个地缘政治风险事件")
        return risks
    
    def _get_regions_for_symbol(self, symbol: str) -> list[str]:
        """获取品种相关的地区"""
        regions = []
        for region, data in self.REGION_SYMBOL_MAP.items():
            if symbol in data.get("affected_symbols", []):
                regions.append(region)
        return regions if regions else ["中东"]  # 默认关注中东
    
    def _create_risk_from_data(self, risk_data: dict) -> GeopoliticalRisk:
        """从数据创建风险对象"""
        try:
            return GeopoliticalRisk(
                risk_id=risk_data.get("risk_id", ""),
                timestamp=risk_data.get("timestamp", ""),
                region=risk_data.get("region", ""),
                risk_type=risk_data.get("risk_type", ""),
                risk_level=risk_data.get("risk_level", ""),
                affected_commodities=risk_data.get("affected_commodities", []),
                affected_symbols=risk_data.get("affected_symbols", []),
                description=risk_data.get("description", ""),
                impact_analysis=risk_data.get("impact_analysis", ""),
                confidence=risk_data.get("confidence", 0.5),
            )
        except Exception as e:
            logger.warning(f"创建风险对象失败: {e}")
            return None
    
    def analyze_news(self, news_events: list) -> list[GeopoliticalRisk]:
        """
        从新闻事件中分析地缘政治风险
        
        Args:
            news_events: 新闻事件列表
            
        Returns:
            地缘政治风险列表
        """
        risks = []
        
        for event in news_events:
            # 检查是否是地缘政治新闻
            if event.category != "geopolitical":
                continue
            
            # 分析风险类型
            risk_type = self._identify_risk_type(event.title + " " + event.content)
            if not risk_type:
                continue
            
            # 识别地区
            region = self._identify_region(event.title + " " + event.content)
            
            # 确定风险等级
            risk_level = self._determine_risk_level(risk_type, event.title + " " + event.content)
            
            # 确定受影响的品种
            affected_symbols = self._get_affected_symbols(region, risk_type)
            
            # 创建风险对象
            risk = GeopoliticalRisk(
                risk_id=event.event_id,
                timestamp=event.timestamp,
                region=region,
                risk_type=risk_type,
                risk_level=risk_level,
                affected_commodities=self.REGION_SYMBOL_MAP.get(region, {}).get("affected_commodities", []),
                affected_symbols=affected_symbols,
                description=event.title,
                impact_analysis=self.RISK_TYPE_IMPACT.get(risk_type, {}).get("impact", ""),
                confidence=event.confidence,
            )
            
            risks.append(risk)
            
            # 添加到已知风险
            self._add_known_risk(risk)
        
        # 保存已知风险
        self._save_known_risks()
        
        return risks
    
    def _identify_risk_type(self, text: str) -> str:
        """
        识别风险类型
        
        优先识别和平协议，然后是战争、制裁等。
        """
        # 优先检查和平协议（因为和平协议通常包含"和平"、"协议"等词）
        peace_keywords = ["和平", "协议", "停火", "和解", "外交突破"]
        for keyword in peace_keywords:
            if keyword in text:
                return "peace_agreement"
        
        # 然后检查战争/冲突
        war_keywords = ["战争", "军事", "冲突", "攻击", "导弹", "空袭", "轰炸", "入侵"]
        for keyword in war_keywords:
            if keyword in text:
                return "war"
        
        # 检查制裁
        sanctions_keywords = ["制裁", "禁运", "封锁", "冻结资产", "黑名单"]
        for keyword in sanctions_keywords:
            if keyword in text:
                return "sanctions"
        
        # 检查关税
        tariffs_keywords = ["关税", "贸易战", "加征关税", "贸易摩擦", "贸易壁垒"]
        for keyword in tariffs_keywords:
            if keyword in text:
                return "tariffs"
        
        # 检查争端
        dispute_keywords = ["争端", "领土", "领海", "主权", "外交"]
        for keyword in dispute_keywords:
            if keyword in text:
                return "dispute"
        
        return ""
    
    def _identify_region(self, text: str) -> str:
        """识别地区"""
        for region, keywords in self.REGION_KEYWORDS.items():
            for keyword in keywords:
                if keyword in text:
                    return region
        return "中东"  # 默认中东
    
    def _determine_risk_level(self, risk_type: str, text: str) -> str:
        """确定风险等级"""
        # 获取默认等级
        default_level = self.RISK_TYPE_IMPACT.get(risk_type, {}).get("default_level", "low")
        
        # 根据关键词调整
        high_keywords = ["战争", "军事", "攻击", "导弹", "空袭", "轰炸", "入侵", "全面"]
        medium_keywords = ["制裁", "禁运", "封锁", "关税", "贸易战", "紧张"]
        
        for keyword in high_keywords:
            if keyword in text:
                return "high"
        
        for keyword in medium_keywords:
            if keyword in text:
                return "medium"
        
        return default_level
    
    def _get_affected_symbols(self, region: str, risk_type: str) -> list[str]:
        """获取受影响的品种"""
        region_data = self.REGION_SYMBOL_MAP.get(region, {})
        return region_data.get("affected_symbols", [])
    
    def _add_known_risk(self, risk: GeopoliticalRisk):
        """添加到已知风险"""
        # 检查是否已存在
        for existing_risk in self.known_risks:
            if existing_risk.get("risk_id") == risk.risk_id:
                return
        
        # 添加新风险
        risk_data = {
            "risk_id": risk.risk_id,
            "timestamp": risk.timestamp,
            "region": risk.region,
            "risk_type": risk.risk_type,
            "risk_level": risk.risk_level,
            "affected_commodities": risk.affected_commodities,
            "affected_symbols": risk.affected_symbols,
            "description": risk.description,
            "impact_analysis": risk.impact_analysis,
            "confidence": risk.confidence,
        }
        
        self.known_risks.append(risk_data)
        
        # 限制已知风险数量
        if len(self.known_risks) > 100:
            self.known_risks = self.known_risks[-100:]


# 测试代码
if __name__ == "__main__":
    # 配置日志
    logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")
    
    # 测试地缘政治风险追踪
    tracker = GeopoliticalTracker()
    
    # 测试原油相关的地缘政治风险
    print("=== 测试原油地缘政治风险 ===")
    risks = tracker.track(symbol="SC")
    for risk in risks:
        print(f"[{risk.region}] {risk.risk_type} - {risk.risk_level}")
        print(f"  描述：{risk.description}")
        print(f"  影响：{risk.impact_analysis}")
        print(f"  受影响品种：{risk.affected_symbols}")
        print()
    
    # 测试从新闻中分析地缘政治风险
    print("=== 测试从新闻中分析地缘政治风险 ===")
    from trend_scanner.models import NewsEvent
    
    # 模拟新闻事件
    test_news = [
        NewsEvent(
            event_id="test_1",
            timestamp=datetime.now().isoformat(),
            source="测试",
            title="美伊和平协议达成，战争风险消退",
            content="美国与伊朗宣布达成和平协议，双方停止军事行动",
            category="geopolitical",
            impact="negative",
            keywords=["美伊", "和平", "协议"],
            affected_symbols=["SC"],
            confidence=0.9,
        ),
    ]
    
    risks = tracker.analyze_news(test_news)
    for risk in risks:
        print(f"[{risk.region}] {risk.risk_type} - {risk.risk_level}")
        print(f"  描述：{risk.description}")
        print(f"  影响：{risk.impact_analysis}")
        print()