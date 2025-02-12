from astrbot.api.event import filter, AstrMessageEvent, MessageEventResult
from astrbot.api.star import Context, Star, register
from astrbot.api import logger
from astrbot.api.all import *
import inspect
from pathlib import Path
from openai import OpenAI
import base64
import os
from queue import Queue
from astrbot.core.provider.entites import LLMResponse
'''---------------------------------------------------'''
@register("astrbot_plugin_morevits", "达莉娅",
          "硅基流动利用用户的参考音频进行文本转语音的功能，内置了一个测试用的三月七（填写api就可用）",
          "1.0.6")
class MyPlugin(Star):
    def __init__(self, context: Context, config: dict):
        super().__init__(context)
        self.output = Queue()
        self.trash = Queue()
        self.chain_message = CommandResult()
        self.counter = 0
        self.flag_mode = 1
        self.enabled = True
        self.config = config
        self.base64_audio = ''
        self.api_url = 'https://api.siliconflow.cn/v1'
        self.api_name = config.get('name', 'FunAudioLLM/CosyVoice2-0.5B')
        self.music_mp3 = config.get('参考音频文件', './data/plugins/astrbot_plugin_morevits/三月七.mp3')
        self.music_text = config.get('参考音频文本',
                                     '所有没见过的东西都要拍下来，这样就不忘啦，等等我！'
                                     '这个列车长绝对喜欢。'
                                     '唔，这个姿势，嗐，真是不会拍照呢。'
                                     '茄子！怎么样怎么样，很有意思吧？'
                                     '嗯？你怎么还在发呆？')
        self.music_url = config.get('参考音频url', '')
        self.api_key = config.get('apikey', '')

        if not self.api_name:
            self.api_name = 'FunAudioLLM/CosyVoice2-0.5B'
        if not self.music_mp3:
                self.music_mp3 = './data/plugins/astrbot_plugin_morevits/三月七.mp3'
        if not self.music_text:
            self.music_text = ('所有没见过的东西都要拍下来，这样就不忘啦，等等我！'
                               '这个列车长绝对喜欢。'
                               '唔，这个姿势，嗐，真是不会拍照呢。'
                               '茄子！怎么样怎么样，很有意思吧？'
                               '嗯？你怎么还在发呆？')
        if not self.music_url:
            self.music_url = ''

        if not os.path.exists(self.music_mp3):
            logger.error(f"未检测到音频文件:{self.music_mp3}")
        else:
            logger.info(f"检测到音频文件:{self.music_mp3}")

    '''---------------------------------------------------'''

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

    '''---------------------------------------------------'''

    @filter.command("vitspro")
    async def switch(self, event: AstrMessageEvent):
        '''这是一个插件开关指令'''
        message_str = event.message_str  # 用户发的纯文本消息字符串
        message_chain = event.get_messages()  # 用户所发的消息的消息链
        logger.info(message_chain)
        user_name = event.get_sender_name()
        user_id = event.get_sender_id()
        time = event.message_obj.timestamp
        chain1 = [
            At(qq=user_id),  # At 消息发送者
            Plain(f"\n插件已经启动"),
            Face(id=337),
            Image.fromURL(
                "https://i0.hdslb.com/bfs/article/bc0ba0646cb50112270da4811799557789b374e3.gif@1024w_820h.avif"),
            # 从 URL 发送图片
        ]
        chain2 = [
            At(qq=user_id),  # At 消息发送者
            Plain(f"\n插件已经关闭"),
            Face(id=337),
            Image.fromURL(
                "https://i0.hdslb.com/bfs/article/bc0ba0646cb50112270da4811799557789b374e3.gif@1024w_820h.avif"),
            # 从 URL 发送图片
        ]
        self.enabled = not self.enabled
        if self.enabled:
            yield event.chain_result(chain1)
        else:
            yield event.chain_result(chain2)

    '''---------------------------------------------------'''
    @filter.on_decorating_result()
    async def on_decorating_result(self, event: AstrMessageEvent):
        result = event.get_result()
        text = result.get_plain_text()
        if not result.chain:
            logger.info(f"返回消息为空,pass")
            return
        if not result.is_llm_result():
            logger.info(f"非LLM消息,pass")
            return
        logger.info(f"LLM返回的文本是：{text}")
        adapter_name = event.get_platform_name()
        if not self.enabled:
            return
        if not self.api_key:
            chain1 = CommandResult().message("文字转语音错误，API配置错误")
            await event.send(chain1)
            return
        if self.flag_mode == 2:
            if not self.music_url:
                chain2 = CommandResult().message("文字转语音错误，music_url配置错误")
                await event.send(chain2)
                return
        if adapter_name == "qq_official":
            logger.info("检测为官方机器人，自动忽略转语音请求")
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
            result.chain.remove(Plain(text))
            if not result.chain:
                logger.info(f"无富文本消息，pass")
            else:
                await event.send(result)
                logger.info(f"富文本消息发送成功")
            result.chain = [Record(file=output_audio_path)]
        else:
            logger.error(f"发生未知错误!")
            chain3 = CommandResult().message(f"文字转语音失败，发生未知错误!")
            await event.send(chain3)
            return

    def dynamic_timbre(self,text):
        client = OpenAI(
            api_key=self.api_key,
            base_url=self.api_url
        )
        with client.audio.speech.with_streaming_response.create(
                model=self.api_name,  # 发送模型名称
                voice="",  # 此处传入空值，表示使用动态音色
                input=text,
                response_format="mp3",
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
                response_format="mp3",
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
        output_audio_path = f"./data/plugins/astrbot_plugin_moreVITS/voice{self.counter}.mp3"
        self.output.put(output_audio_path)
        return output_audio_path
    '''---------------------------------------------------'''

    @filter.after_message_sent()
    async def after_message_sent(self, event: AstrMessageEvent):
        if not self.trash.empty():
            output_audio_path = self.trash.get()
            if os.path.exists(output_audio_path):
                os.remove(output_audio_path)
                logger.warning(f"已清除1个trash，队列中还有【{self.trash.qsize()}】条trash待清除")

