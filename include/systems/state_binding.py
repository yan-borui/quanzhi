# -*- coding: utf-8 -*-
"""
StateBindingSystem - 状态绑定系统

管理技能效果与特定目标的绑定关系。
部分技能效果与特定目标绑定，对新目标使用同一技能时，自动解除旧目标的状态。
支持"对另一人使用时第一个破"的机制。

接口设计：
- 绑定技能与目标
- 检查技能是否已激活并绑定目标
- 切换目标时自动解除旧状态
"""

from typing import Optional, Any, Callable, Dict, List, Tuple


class StateBinding:
    """状态绑定类"""
    
    def __init__(self,
                 skill_name: str,
                 source: Any,
                 target: Any,
                 on_bind: Optional[Callable[[Any, Any], None]] = None,
                 on_unbind: Optional[Callable[[Any, Any], None]] = None,
                 state_name: str = ""):
        """
        初始化状态绑定
        
        Args:
            skill_name: 技能名称
            source: 施法者（技能来源）
            target: 目标角色
            on_bind: 绑定时的回调函数，接受(source, target)
            on_unbind: 解绑时的回调函数，接受(source, target)
            state_name: 状态名称（可选，用于标识具体的状态效果）
        """
        self.skill_name = skill_name
        self.source = source
        self.target = target
        self.on_bind = on_bind
        self.on_unbind = on_unbind
        self.state_name = state_name if state_name else skill_name
        self.is_active = True
        
        # 执行绑定回调
        if self.on_bind:
            self.on_bind(source, target)
    
    def unbind(self):
        """解除绑定"""
        if not self.is_active:
            return
        
        self.is_active = False
        
        # 执行解绑回调
        if self.on_unbind:
            self.on_unbind(self.source, self.target)
    
    def get_source_id(self) -> int:
        """获取施法者ID"""
        return id(self.source)
    
    def get_target_id(self) -> int:
        """获取目标ID"""
        return id(self.target)


class StateBindingSystem:
    """状态绑定管理系统"""
    
    def __init__(self):
        """初始化状态绑定系统"""
        # 存储绑定关系: (source_id, skill_name) -> StateBinding
        # 一个技能在同一时间只能绑定一个目标
        self.bindings: Dict[Tuple[int, str], StateBinding] = {}
        
        # 反向索引: target_id -> List[(source_id, skill_name)]
        # 用于快速查找目标身上的所有绑定
        self.target_bindings: Dict[int, List[Tuple[int, str]]] = {}
    
    def bind_state(self,
                   skill_name: str,
                   source: Any,
                   target: Any,
                   on_bind: Optional[Callable[[Any, Any], None]] = None,
                   on_unbind: Optional[Callable[[Any, Any], None]] = None,
                   state_name: str = "",
                   auto_unbind_old: bool = True) -> StateBinding:
        """
        创建状态绑定
        
        Args:
            skill_name: 技能名称
            source: 施法者
            target: 目标角色
            on_bind: 绑定时的回调函数
            on_unbind: 解绑时的回调函数
            state_name: 状态名称
            auto_unbind_old: 是否自动解除旧绑定（默认True）
            
        Returns:
            StateBinding: 创建的绑定对象
        """
        source_id = id(source)
        target_id = id(target)
        key = (source_id, skill_name)
        
        source_name = source.get_name() if hasattr(source, 'get_name') else str(source)
        target_name = target.get_name() if hasattr(target, 'get_name') else str(target)
        
        # 如果已有绑定且目标不同，自动解除旧绑定
        if auto_unbind_old and key in self.bindings:
            old_binding = self.bindings[key]
            old_target_id = old_binding.get_target_id()
            
            if old_target_id != target_id:
                old_target_name = old_binding.target.get_name() if hasattr(old_binding.target, 'get_name') else str(old_binding.target)
                print(f"[状态绑定] {source_name} 的 '{skill_name}' 从 {old_target_name} 解绑")
                self.unbind_state(source, skill_name)
        
        # 创建新绑定
        binding = StateBinding(skill_name, source, target, on_bind, on_unbind, state_name)
        self.bindings[key] = binding
        
        # 更新反向索引
        if target_id not in self.target_bindings:
            self.target_bindings[target_id] = []
        
        if key not in self.target_bindings[target_id]:
            self.target_bindings[target_id].append(key)
        
        print(f"[状态绑定] {source_name} 的 '{skill_name}' 绑定到 {target_name}")
        
        return binding
    
    def unbind_state(self, source: Any, skill_name: str) -> bool:
        """
        解除指定技能的绑定
        
        Args:
            source: 施法者
            skill_name: 技能名称
            
        Returns:
            bool: 是否成功解绑
        """
        source_id = id(source)
        key = (source_id, skill_name)
        
        if key not in self.bindings:
            return False
        
        binding = self.bindings[key]
        target_id = binding.get_target_id()
        
        # 执行解绑
        binding.unbind()
        
        # 移除绑定记录
        del self.bindings[key]
        
        # 更新反向索引
        if target_id in self.target_bindings:
            if key in self.target_bindings[target_id]:
                self.target_bindings[target_id].remove(key)
            
            # 如果目标没有其他绑定，移除空列表
            if not self.target_bindings[target_id]:
                del self.target_bindings[target_id]
        
        source_name = source.get_name() if hasattr(source, 'get_name') else str(source)
        print(f"[状态绑定] {source_name} 的 '{skill_name}' 已解绑")
        
        return True
    
    def unbind_all_from_target(self, target: Any):
        """
        解除目标身上的所有绑定
        
        Args:
            target: 目标角色
        """
        target_id = id(target)
        
        if target_id not in self.target_bindings:
            return
        
        # 获取所有需要解绑的键（复制列表避免迭代时修改）
        keys_to_unbind = self.target_bindings[target_id].copy()
        
        for key in keys_to_unbind:
            if key in self.bindings:
                binding = self.bindings[key]
                binding.unbind()
                del self.bindings[key]
        
        # 清空反向索引
        del self.target_bindings[target_id]
        
        target_name = target.get_name() if hasattr(target, 'get_name') else str(target)
        print(f"[状态绑定] {target_name} 身上的所有绑定已清除 (数量: {len(keys_to_unbind)})")
    
    def unbind_all_from_source(self, source: Any):
        """
        解除施法者的所有绑定
        
        Args:
            source: 施法者
        """
        source_id = id(source)
        
        # 查找所有该施法者的绑定
        keys_to_unbind = [key for key in self.bindings.keys() if key[0] == source_id]
        
        for key in keys_to_unbind:
            binding = self.bindings[key]
            target_id = binding.get_target_id()
            
            # 执行解绑
            binding.unbind()
            del self.bindings[key]
            
            # 更新反向索引
            if target_id in self.target_bindings:
                if key in self.target_bindings[target_id]:
                    self.target_bindings[target_id].remove(key)
                
                if not self.target_bindings[target_id]:
                    del self.target_bindings[target_id]
        
        if keys_to_unbind:
            source_name = source.get_name() if hasattr(source, 'get_name') else str(source)
            print(f"[状态绑定] {source_name} 的所有绑定已清除 (数量: {len(keys_to_unbind)})")
    
    def is_bound(self, source: Any, skill_name: str) -> bool:
        """
        检查技能是否已绑定
        
        Args:
            source: 施法者
            skill_name: 技能名称
            
        Returns:
            bool: 是否已绑定
        """
        source_id = id(source)
        key = (source_id, skill_name)
        
        return key in self.bindings and self.bindings[key].is_active
    
    def get_bound_target(self, source: Any, skill_name: str) -> Optional[Any]:
        """
        获取技能当前绑定的目标
        
        Args:
            source: 施法者
            skill_name: 技能名称
            
        Returns:
            Optional[Any]: 绑定的目标，如果未绑定则返回None
        """
        source_id = id(source)
        key = (source_id, skill_name)
        
        if key in self.bindings and self.bindings[key].is_active:
            return self.bindings[key].target
        
        return None
    
    def get_binding(self, source: Any, skill_name: str) -> Optional[StateBinding]:
        """
        获取绑定对象
        
        Args:
            source: 施法者
            skill_name: 技能名称
            
        Returns:
            Optional[StateBinding]: 绑定对象，如果不存在则返回None
        """
        source_id = id(source)
        key = (source_id, skill_name)
        
        return self.bindings.get(key)
    
    def get_target_bindings(self, target: Any) -> List[Tuple[Any, str]]:
        """
        获取目标身上的所有绑定
        
        Args:
            target: 目标角色
            
        Returns:
            list[tuple[Any, str]]: 绑定列表，每项为(施法者, 技能名)
        """
        target_id = id(target)
        
        if target_id not in self.target_bindings:
            return []
        
        result = []
        for key in self.target_bindings[target_id]:
            if key in self.bindings:
                binding = self.bindings[key]
                result.append((binding.source, binding.skill_name))
        
        return result
