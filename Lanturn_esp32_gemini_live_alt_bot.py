#
# Lanturn - made for the Google + Pipecat Hackathon - Gemini Live ESP32 Alternative Bot (no vision)
#
# Based on Pipecat's Gemini Live video example:
# https://github.com/pipecat-ai/pipecat/blob/main/examples/foundational/26c-gemini-live-video.py
#
#
#


import os

from dotenv import load_dotenv
from loguru import logger

from pipecat.audio.vad.silero import SileroVADAnalyzer
from pipecat.audio.vad.vad_analyzer import VADParams
from pipecat.frames.frames import LLMRunFrame
from pipecat.pipeline.pipeline import Pipeline
from pipecat.pipeline.runner import PipelineRunner
from pipecat.pipeline.task import PipelineParams, PipelineTask
from pipecat.processors.aggregators.openai_llm_context import OpenAILLMContext
from pipecat.runner.types import RunnerArguments
from pipecat.runner.utils import create_transport
from pipecat.services.google.gemini_live.llm import GeminiLiveLLMService
from pipecat.transports.base_transport import BaseTransport, TransportParams
from pipecat.transports.daily.transport import DailyParams
from pipecat.transports.websocket.fastapi import FastAPIWebsocketParams

load_dotenv(override=True)


# Function handlers for the LLM
search_tool = {"google_search": {}}
tools = [search_tool]

system_instruction = """
1.You are Lanturn, a helpful AI assistant running on an E.S.P.32 device.
2. THE GOLDEN RULE: BREVITY AND IMPACT
Your primary directive is to be brief and impactful. All responses must be under 50 words. Prioritize the most critical information to help the user, this is usually the first 1-3 action steps. If a topic requires more detail, you must first provide the brief overview and then offer to provide more information only if asked.
3. CORE DIRECTIVES
Safety First: For any Electrical or dangerous repair query, your first sentence could be a safety warning (e.g., "First, for safety, make sure you unplug the appliance."). If the task presents high risks, advise consulting a professional.
Structured DIY Guidance: For DIY tasks, provide guidance in a numbered list format. Limit lists to a maximum of 3-4 steps per response to adhere to The Golden Rule.
Tool Usage: Use Google Search for information you don't know, including current weather, local business information, and up-to-date repair guides or part recommendations. 
Concise Summaries: When reporting search results, summarize them in one clear, concise sentence.
Maintain Flow: Avoid ending responses with conversational boilerplate like "Do you have any more questions?" Let the conversation flow naturally.
Pronunciation: Pronounce numbers naturally (e.g., "two-hundred-fifty," not "two five zero").
4. FEW-SHOT EXAMPLES
USER PROMPT (Audio): "How do I make a pocket hole?"
Lanturn (Ideal Response): "Of course. To make a pocket hole, you'll need a specialized pocket hole jig. Do you have one, and could you tell me what brand it is? The setup can vary slightly between models."
Example 2: What's the weather in Tokyo?    
USER PROMPT (Audio): "What's the weather in Tokyo?"
Lanturn (Ideal Response): "The weather in Tokyo is sunny and 70 degrees Fahrenheit. The humidity is 50%."

You can use the search_tool to access information from the Google Search API.
Your output will be converted to audio so don't include special characters in your answers.
Respond to what the user said in a creative, helpful, and engaging way.
Keep your responses concise since you're running on a small device.
"""


# We store functions so objects (e.g. SileroVADAnalyzer) don't get
# instantiated. The function will be called when the desired transport gets
# selected.
transport_params = {
    "daily": lambda: DailyParams(
        audio_in_enabled=True,
        audio_out_enabled=True,
        # set stop_secs to something roughly similar to the internal setting
        # of the Multimodal Live api, just to align events. This doesn't really
        # matter because we can only use the Multimodal Live API's phrase
        # endpointing, for now.
        vad_analyzer=SileroVADAnalyzer(params=VADParams(stop_secs=0.5)),
    ),
    "twilio": lambda: FastAPIWebsocketParams(
        audio_in_enabled=True,
        audio_out_enabled=True,
        # set stop_secs to something roughly similar to the internal setting
        # of the Multimodal Live api, just to align events. This doesn't really
        # matter because we can only use the Multimodal Live API's phrase
        # endpointing, for now.
        vad_analyzer=SileroVADAnalyzer(params=VADParams(stop_secs=0.5)),
    ),
    "webrtc": lambda: TransportParams(
        audio_in_enabled=True,
        audio_out_enabled=True,
        # set stop_secs to something roughly similar to the internal setting
        # of the Multimodal Live api, just to align events. This doesn't really
        # matter because we can only use the Multimodal Live API's phrase
        # endpointing, for now.
        vad_analyzer=SileroVADAnalyzer(params=VADParams(stop_secs=0.5)),
    ),
}


async def run_bot(transport: BaseTransport, runner_args: RunnerArguments):
    logger.info(f"Starting bot")

    # Initialize the Gemini Multimodal Live model
    llm = GeminiLiveLLMService(
        api_key=os.getenv("GOOGLE_API_KEY"),
        voice_id="Charon",  # Aoede, Charon, Fenrir, Kore, Puck
        system_instruction=system_instruction,
        tools=tools,
    )

    context = OpenAILLMContext(
        [
            {
                "role": "user",
                "content": "Start by greeting the user warmly, introducing yourself. Be friendly and engaging to set a positive tone for the interaction.",
            }
        ],
    )
    context_aggregator = llm.create_context_aggregator(context)

    pipeline = Pipeline(
        [
            transport.input(),  # Transport user input
            context_aggregator.user(),  # User responses
            llm,  # LLM
            transport.output(),  # Transport bot output
            context_aggregator.assistant(),  # Assistant spoken responses
        ]
    )

    task = PipelineTask(
        pipeline,
        params=PipelineParams(
            enable_metrics=True,
            enable_usage_metrics=True,
        ),
        idle_timeout_secs=runner_args.pipeline_idle_timeout_secs,
    )

    @transport.event_handler("on_client_connected")
    async def on_client_connected(transport, client):
        logger.info(f"Client connected")
        # Kick off the conversation.
        await task.queue_frames([LLMRunFrame()])

    @transport.event_handler("on_client_disconnected")
    async def on_client_disconnected(transport, client):
        logger.info(f"Client disconnected")
        await task.cancel()

    runner = PipelineRunner(handle_sigint=runner_args.handle_sigint)

    await runner.run(task)


async def bot(runner_args: RunnerArguments):
    """Main bot entry point compatible with Pipecat Cloud."""
    transport = await create_transport(runner_args, transport_params)
    await run_bot(transport, runner_args)


if __name__ == "__main__":
    from pipecat.runner.run import main

    main()