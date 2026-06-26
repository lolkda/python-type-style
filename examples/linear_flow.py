"""线性流程示例,展示直线脚本如何避免薄 helper 和无意义包装模型。

本示例刻意不从 examples/_shared.py 导入锚点模型:它演示的是"线性脚本结构",
本身不定义任何对外契约(outward contract),因此不需要 _shared.py 提供的
User / BaseResponse[T] 等共享模型。其它示例文件因为要复用对外契约才统一导入 _shared.py。

存在性判据(Priority 0)优先于装饰:下面的 BAD 形状即便补上中文 docstring、类型、
keyword-only 也仍是违规,因为它们根本不该作为独立函数/模型存在。
"""

from time import sleep


# BAD: 以下形状仅作审查对照,保持注释而非可运行代码,避免 py_compile 把反模式判为"通过"。
# def wait_between_batches(*, seconds: float) -> None:        # 只包 sleep(),内联回调用点 → P0
#     sleep(seconds)
# def send_prompt_once(*, agent, prompt):                     # 只包一次 run_sync(),非适配器 → P0
#     return agent.run_sync(prompt=prompt)
# def send_config_prompt_once(*, agent, prompt):              # 转发链中间层,只转交参数 → P0
#     return send_prompt_once(agent=agent, prompt=prompt)
# def send_batch_once(*, agent, prompts):                     # 转发链顶层,只命名一个步骤 → P0
#     return [send_config_prompt_once(agent=agent, prompt=p) for p in prompts]
# class ChatBatch(BaseModel):                                 # 只包本地 list,unwrap 后无损失 → P0
#     items: list[str]


class DemoAgent:
    """演示用外部调用 test double,仅服务本示例,不代表真实 SDK 客户端。

    注:test double 本身受 skill 豁免;此处仍补全中文 docstring,使示例端到端自洽,
    并明确它的身份是替身,不是被推荐为生产代码的外部客户端封装。
    """

    def __init__(self, *, prefix: str) -> None:
        """
        初始化演示调用对象,记录拼接在响应前的前缀。

        Args:
            prefix: 拼接在每条响应前的演示前缀。

        Returns:
            无返回值。
        """
        self.prefix = prefix

    def run_sync(self, *, prompt: str) -> str:
        """
        执行单次演示调用,返回带前缀的同步结果。

        Args:
            prompt: 需要发送的提示词。

        Returns:
            str: 带有演示前缀的调用结果。
        """
        return f"{self.prefix}: {prompt}"


def main(*, prompts: list[str], wait_seconds: float = 0.0) -> list[str]:
    """
    按直线流程依次发送提示词并收集结果。

    设置、单次外部调用、结果收集、等待全部留在同一个高层流程里:这些步骤都只是
    "接下来发生什么",把任何一步抽成独立 helper 都会让调用点更难读,因此保持内联。

    Args:
        prompts: 需要按顺序发送的提示词列表。
        wait_seconds: 每次调用后的等待秒数,大于零时才真正休眠。

    Returns:
        list[str]: 每个提示词对应的演示响应,顺序与输入一致。
    """
    agent = DemoAgent(prefix="demo")
    responses: list[str] = []
    for prompt in prompts:
        responses.append(agent.run_sync(prompt=prompt))
        if wait_seconds > 0:
            sleep(wait_seconds)
    return responses


if __name__ == "__main__":
    print(main(prompts=["first", "second"]))
