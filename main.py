import random
from astrbot.api.event import filter, AstrMessageEvent, MessageEventResult
from astrbot.api.all import *
from openai import OpenAI
import base64
import os
import json
from queue import Queue
import re
'''---------------------------------------------------'''
@register("astrbot_plugin_moreVITS", "达莉娅",
          "硅基流动利用用户的参考音频进行文本转语音的功能，内置了一个测试用的三月七（填写api就可用）",
          "v1.2.0")
class MyPlugin(Star):
    def __init__(self, context: Context, config: dict):
        super().__init__(context)
        self.fg = False
        self.rooms = []
        self.output = Queue()
        self.trash = Queue()
        self.chain_message = CommandResult()
        self.counter = 0
        self.flag_mode = 1
        self.ran = config.get('概率触发', 0.1)
        self.enabled = True
        self.trap = True
        self.config = config
        self.base64_audio = ''
        self.api_url = 'https://api.siliconflow.cn/v1'
        self.api_name = config.get('name', 'FunAudioLLM/CosyVoice2-0.5B')
        self.music_mp3 = config.get('参考音频文件', './data/plugins/astrbot_plugin_morevits/三月七.mp3')
        self.music_text = config.get('参考音频文本','')
        self.music_url = config.get('参考音频url', '')
        self.music_text_file = config.get('参考音频文本txt模式', '')
        self.api_key = config.get('apikey', '')
        self.fg = config.get('是否同时回复文字内容开关', False)
        self.trap = config.get('过滤开关', True)
        if not self.ran:
            self.ran = 0.5
        if os.path.exists(self.music_text_file):
            with open(self.music_text_file, 'r',encoding="utf-8") as file:
                self.music_text = file.read()
        if not self.api_name:
            self.api_name = 'FunAudioLLM/CosyVoice2-0.5B'
        if not self.music_mp3:
                self.music_mp3 = './data/plugins/astrbot_plugin_morevits/三月七.mp3'
        if not self.music_text:
            self.music_text = "所有没见过的东西都要拍下来，这样就不会忘了，等等我。这个列车长绝对喜欢。怎么样怎么样，很有意思吧？你怎么还在发呆？嘿嘿，第一张合照就归我啦。你没事吧，听得清我说话吗？记不记得自己叫什么名字？那可麻烦了，能努力回忆一下吗，你的名字是？那你自己小心哦。要不你把这个拿上吧。"
        if not self.music_url:
            self.music_url = ''
        self.file_path = './data/plugins/astrbot_plugin_morevits/data.jsonl'
        if not os.path.exists(self.file_path):
            self.save_game()
            print(f"文件 {self.file_path} 不存在，已创建并初始化。")
        else:
            print(f"文件 {self.file_path} 已存在，跳过创建。")
        self.load_game()
        if not os.path.exists(self.music_mp3):
            logger.error(f"未检测到音频文件:{self.music_mp3}")
        else:
            logger.info(f"检测到音频文件:{self.music_mp3}")

    '''---------------------------------------------------'''
    def load_game(self):
        dicts = []
        with open(self.file_path, 'r') as f:
            for line in f:
                dicts.append(json.loads(line.strip()))
        # 分配到各自的字典
        if not dicts:  # 如果 dicts 为空
            logger.warning("加载的数据为空")
            return
        else:
            self.rooms = dicts[0]
            return

    def save_game(self):
        with open(self.file_path, 'w') as f:
            f.write(json.dumps(self.rooms) + '\n')
    @filter.command("change")
    async def change(self, event: AstrMessageEvent, a: int):
        '''/change 1使用参考音频文件，2为参考音频url，默认1'''
        if a == 1:
            self.flag_mode = 1
            yield event.plain_result(f"使用参考音频文件模式")
        else:
            self.flag_mode = 2
            yield event.plain_result(f"使用参考音频url模式")

    '''---------------------------------------------------'''

    @filter.command_group("music")
    async def music(self, event: AstrMessageEvent):
        '''上传参考音频url【/music addurl】/参考音频文本【/music addtext】'''
        pass

    @music.command("addurl")
    async def add(self, event: AstrMessageEvent, music_url: str):
        '''上传参考音频url'''
        self.music_url = music_url
        yield event.plain_result(f"参考音频url上传完成")

    @music.command("addtext")
    async def sub(self, event: AstrMessageEvent, music_text: str):
        '''上传参考音频文本'''
        self.music_text = music_text
        yield event.plain_result(f"参考音频文本上传完成")
    @filter.command("文本开关")
    async def trapsss(self, event: AstrMessageEvent):
        '''这是一个开启语音原文一起发指令'''
        user_id = event.get_sender_id()
        chain1 = [
            At(qq=user_id),  # At 消息发送者
            Plain(f"\n过滤已经启动"),
            Face(id=337),
        ]
        chain2 = [
            At(qq=user_id),  # At 消息发送者
            Plain(f"\n过滤已经关闭"),
            Face(id=337),
        ]
        self.fg = not self.fg
        if self.trap:
            yield event.chain_result(chain1)
        else:
            yield event.chain_result(chain2)
    @filter.command("过滤开关")
    async def trap(self, event: AstrMessageEvent):
        '''这是一个过滤颜表情开关指令'''
        user_id = event.get_sender_id()
        chain1 = [
            At(qq=user_id),  # At 消息发送者
            Plain(f"\n过滤已经启动"),
            Face(id=337),
        ]
        chain2 = [
            At(qq=user_id),  # At 消息发送者
            Plain(f"\n过滤已经关闭"),
            Face(id=337),
        ]
        self.trap = not self.trap
        if self.trap:
            yield event.chain_result(chain1)
        else:
            yield event.chain_result(chain2)
    '''---------------------------------------------------'''

    @filter.command("morevits")
    async def switch(self, event: AstrMessageEvent):
        '''这是一个插件开关指令'''
        user_id = event.get_sender_id()
        room  = event.get_group_id()
        chain1 = [
            At(qq=user_id),  # At 消息发送者
            Plain(f"\n本群插件已经启动（仅本群）"),
            Face(id=337),
            Image.fromURL(
                "https://i0.hdslb.com/bfs/article/bc0ba0646cb50112270da4811799557789b374e3.gif@1024w_820h.avif"),
            # 从 URL 发送图片
        ]
        chain2 = [
            At(qq=user_id),  # At 消息发送者
            Plain(f"\n本群插件已经关闭（仅本群）"),
            Face(id=337),
            Image.fromURL(
                "https://i0.hdslb.com/bfs/article/bc0ba0646cb50112270da4811799557789b374e3.gif@1024w_820h.avif"),
            # 从 URL 发送图片
        ]
        if room in self.rooms:
            self.rooms.remove(room)
            self.save_game()
            yield event.chain_result(chain1)
        else:
            self.rooms.append(room)
            self.save_game()
            yield event.chain_result(chain2)

    '''---------------------------------------------------'''
    @filter.on_decorating_result(priority=100)
    async def on_decorating_result(self, event: AstrMessageEvent):
        result = event.get_result()
        text = result.get_plain_text()
        room = event.get_group_id()
        adapter_name = event.get_platform_name()
        if adapter_name == "qq_official":
            logger.info("检测为官方机器人，自动忽略转语音请求")
            return
        if not result.chain:
            logger.info(f"返回消息为空,pass")
            return
        if not result.is_llm_result():
            logger.info(f"非LLM消息,pass")
            return
        if room in self.rooms :
            logger.info(f"本群插件已关闭")
            return
        random_float = random.random()
        if  random_float>=self.ran:
            logger.info("随机取消转语音")
            return
        elif self.fg:
            text = self.remove_complex_emoticons(text)
            await event.send(result)
        logger.info(f"LLM返回的文本是：{text}")
        result.chain.remove(Plain(text))
        if self.trap:
            text = self.remove_complex_emoticons(text)
            logger.info(f"过滤颜表情后的文本是：{text}")
        if not self.api_key:
            chain1 = CommandResult().message("文字转语音错误，API配置错误")
            await event.send(chain1)
            return
        if self.flag_mode == 2:
            if not self.music_url:
                chain2 = CommandResult().message("文字转语音错误，music_url配置错误")
                await event.send(chain2)
                return


        try:
            if self.flag_mode == 1:
                self.dynamic_timbre2(text)
            else:
                self.dynamic_timbre(text)
        except Exception as e:
            chain3 = CommandResult().message(f"文字转语音错误，{e}")
            await event.send(chain3)
            return

        if not self.output.empty():
            output_audio_path = self.output.get()
            self.trash.put(output_audio_path)
            logger.info(f"转语音任务成功执行1次，队列中还有【{self.output.qsize()}】条语音待执行")
            voice = MessageChain()
            voice.chain.append(Record(file=output_audio_path))
            await event.send(voice)
        else:
            logger.error(f"发生未知错误!")
            chain3 = CommandResult().message(f"文字转语音失败，发生未知错误!")
            await event.send(chain3)
            return

    def remove_complex_emoticons(self,text):
        pattern = r"""
                \([^()]+\)              # 匹配括号内的复杂颜表情
                |                       # 或
                [^\u4e00-\u9fff，。？！、]  # 匹配非中文、非标点符号、非空格的字符
        """
        regex = re.compile(pattern, re.VERBOSE)
        cleaned_text = regex.sub('', text)
        return cleaned_text

    def dynamic_timbre(self,text):
        client = OpenAI(
            api_key=self.api_key,
            base_url=self.api_url
        )
        with client.audio.speech.with_streaming_response.create(
                model=self.api_name,  # 发送模型名称
                voice="",  # 此处传入空值，表示使用动态音色
                input=text,
                response_format="wav",
                extra_body={"references": [
                    {
                        "audio": f"{self.music_url}",
                        # 参考音频 url。也支持 base64 格式
                        "text": f"{self.music_text}",  # 参考音频的文字内容
                    }
                ]}
        ) as response:
            output_audio_path = self.queue()
            response.stream_to_file(output_audio_path)

    def dynamic_timbre2(self,text):
        self.base64()
        client = OpenAI(
            api_key=self.api_key,
            base_url=self.api_url
        )
        with client.audio.speech.with_streaming_response.create(
                model=self.api_name,  # 发送模型名称
                voice="",  # 此处传入空值，表示使用动态音色
                input=text,
                response_format="wav",
                extra_body={"references": [
                    {
                        "audio": f"data:audio/mpeg;base64,{self.base64_audio}",
                        # 参考音频 url。也支持 base64 格式
                        "text": f"{self.music_text}",  # 参考音频的文字内容
                    }
                ]}
        ) as response:
            output_audio_path = self.queue()
            response.stream_to_file(output_audio_path)


    def base64(self):
        # 读取音频文件并将其转换为数组
        with open(self.music_mp3, 'rb') as file:
            audio_array = bytearray(file.read())
        # 将音频数组转换为Base64编码
        self.base64_audio = base64.b64encode(audio_array).decode('utf-8')

    def queue(self):
        if self.counter == 20:
            self.counter = 0
        self.counter = self.counter + 1
        output_audio_path = f"./data/plugins/astrbot_plugin_morevits/voice{self.counter}.wav"
        self.output.put(output_audio_path)
        return output_audio_path
    '''---------------------------------------------------'''

    @filter.after_message_sent()
    async def after_message(self, event: AstrMessageEvent):
        if not self.trash.empty():
            output_audio_path = self.trash.get()
            if os.path.exists(output_audio_path):
                os.remove(output_audio_path)
                logger.warning(f"已清除1个trash，队列中还有【{self.trash.qsize()}】条trash待清除")