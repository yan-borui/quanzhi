# -*- coding: utf-8 -*-
"""
CharacterFactory - 角色工厂系统
提供角色创建、注册和管理功能，解耦Game类与具体角色类
"""

from typing import Dict, List, Type, Optional, Callable
from core.character import Character


class CharacterRegistry:
    """角色注册表，管理所有可用的角色类型"""
    
    def __init__(self):
        self._characters: Dict[str, Type[Character]] = {}
        self._metadata: Dict[str, dict] = {}
        
    def register(self, role_id: str, character_class: Type[Character], 
                 display_name: str = None, description: str = None, 
                 stats: dict = None):
        """
        注册一个角色类型
        
        Args:
            role_id: 角色唯一标识符（如 "knight"）
            character_class: 角色类
            display_name: 显示名称（如 "骑士"）
            description: 角色描述
            stats: 角色统计信息
        """
        self._characters[role_id] = character_class
        self._metadata[role_id] = {
            "display_name": display_name or role_id,
            "description": description or "",
            "stats": stats or {},
            "class": character_class
        }
        
    def unregister(self, role_id: str):
        """注销角色类型"""
        if role_id in self._characters:
            del self._characters[role_id]
            del self._metadata[role_id]
            
    def get_character_class(self, role_id: str) -> Optional[Type[Character]]:
        """获取角色类"""
        return self._characters.get(role_id)
        
    def get_metadata(self, role_id: str) -> Optional[dict]:
        """获取角色元数据"""
        return self._metadata.get(role_id)
        
    def list_available_characters(self) -> List[str]:
        """列出所有可用角色ID"""
        return list(self._characters.keys())
        
    def get_all_metadata(self) -> Dict[str, dict]:
        """获取所有角色元数据"""
        return self._metadata.copy()


class CharacterFactory:
    """角色工厂，用于创建角色实例"""
    
    def __init__(self, registry: CharacterRegistry = None):
        self.registry = registry or CharacterRegistry()
        
    def create(self, role_id: str, name: str = None) -> Optional[Character]:
        """
        创建角色实例
        
        Args:
            role_id: 角色ID
            name: 自定义角色名称，如果不提供则使用默认名称
            
        Returns:
            Character实例，如果role_id不存在则返回None
        """
        character_class = self.registry.get_character_class(role_id)
        if not character_class:
            return None
            
        metadata = self.registry.get_metadata(role_id)
        default_name = metadata.get("display_name", role_id) if metadata else role_id
        
        # 创建实例，使用自定义名称或默认名称
        instance = character_class(name if name else default_name)
        return instance
        
    def create_multiple(self, role_configs: List[dict]) -> List[Character]:
        """
        批量创建角色
        
        Args:
            role_configs: 角色配置列表，每个元素为 {"role_id": "knight", "name": "我的骑士"}
            
        Returns:
            角色实例列表
        """
        characters = []
        for config in role_configs:
            role_id = config.get("role_id")
            name = config.get("name")
            if role_id:
                char = self.create(role_id, name)
                if char:
                    characters.append(char)
        return characters
        
    def get_registry(self) -> CharacterRegistry:
        """获取注册表"""
        return self.registry


# 全局注册表和工厂实例
_global_registry = CharacterRegistry()
_global_factory = CharacterFactory(_global_registry)


def get_character_factory() -> CharacterFactory:
    """获取全局角色工厂"""
    return _global_factory


def get_character_registry() -> CharacterRegistry:
    """获取全局角色注册表"""
    return _global_registry


def register_character(role_id: str, character_class: Type[Character],
                       display_name: str = None, description: str = None,
                       stats: dict = None):
    """便捷函数：向全局注册表注册角色"""
    _global_registry.register(role_id, character_class, display_name, description, stats)
