class Narrator:
    def __init__(self, client, model_name):
        self.client = client
        self.model = model_name

    def narrate(self, scene_desc, player_input, system_result, setting):
        """
        生成 GM 的敘事回應
        """
        system_prompt = f"""
        你是 COC 守密人 (GM)。
        【世界觀】{setting.get('visual_style')}
        【氛圍】{setting.get('atmosphere')}
        
        【規則】
        1. 根據 [系統結果] 進行敘事。
        2. 若結果包含檢定 (例如: 檢定成功/失敗)，請描述角色努力的過程。
        3. 若結果包含獲得物品，描述玩家將其收好的動作。
        4. 嚴禁創造不存在的家具或物品。
        5. 繁體中文，懸疑風格，控制在 150 字以內。
        """
        
        user_prompt = f"""
        [當前場景]: {scene_desc}
        [玩家行動]: {player_input}
        [系統判定結果]: {system_result}
        """
        
        try:
            res = self.client.chat(
                model=self.model,
                messages=[
                    {'role': 'system', 'content': system_prompt},
                    {'role': 'user', 'content': user_prompt}
                ]
            )
            return res['message']['content']
        except Exception as e:
            return f"(敘事生成失敗: {e}) \n系統訊息: {system_result}"