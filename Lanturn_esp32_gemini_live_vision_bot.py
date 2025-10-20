#
# Lantern Hackathon - Gemini Live ESP32 Vision Bot
# 
# This bot connects a Gemini Live API to an ESP32 Atoms3r-CAM device
# for voice + vision conversations using WebRTC.
#
# Based on Pipecat's Gemini Live video example:
# https://github.com/pipecat-ai/pipecat/blob/main/examples/foundational/26c-gemini-live-video.py
#

import asyncio
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
from pipecat.runner.utils import (
    create_transport,
    maybe_capture_participant_camera,
)
from pipecat.services.google.gemini_live.llm import GeminiLiveLLMService
from pipecat.transports.base_transport import BaseTransport, TransportParams

# Load environment variables
load_dotenv(override=True)


# We store functions so objects (e.g. SileroVADAnalyzer) don't get
# instantiated. The function will be called when the desired transport gets
# selected.
transport_params = {
    "webrtc": lambda: TransportParams(
        audio_in_enabled=True,
        audio_out_enabled=True,
        video_in_enabled=True,  # Enable video input for camera frames
        video_out_enabled=False,  # Disable local video track to avoid aiortc H264 encode on server
        # set stop_secs to something roughly similar to the internal setting
        # of the Multimodal Live api, just to align events.
        vad_analyzer=SileroVADAnalyzer(params=VADParams(stop_secs=0.5)),
    ),
}


async def run_bot(transport: BaseTransport, runner_args: RunnerArguments):
    logger.info(f"Starting Lantern Gemini Live VISION bot for ESP32")

    # Create the Gemini Multimodal Live LLM service with vision enabled
    system_instruction = """
    1. You are Lantern, a helpful AI assistant with VISION running on an E.S.P.32 device with a camera.
    2. You're participating in a hackathon demonstration where you showcase
    voice AI and VISION capabilities on embedded hardware.
    3. THE GOLDEN RULE: BREVITY AND IMPACT: Your primary directive is to be brief and impactful. All responses must be under 50 words. Prioritize the most critical information to help the user, this is usually the first 1-3 action steps. If a topic requires more detail, you must first provide the brief overview and then offer to provide more information only if asked.
    4. CORE DIRECTIVES:
    Safety First: For any Electrical or dangerous repair query, your first sentence could be a safety warning (e.g., "First, for safety, make sure you unplug the appliance."). If the task presents high risks, advise consulting a professional.
    Structured DIY Guidance: For DIY tasks, provide guidance in a numbered list format. Limit lists to a maximum of 3-4 steps per response to adhere to The Golden Rule.
    Tool Usage: Use Google Search for information you don't know, including current weather, local business information, and up-to-date repair guides or part recommendations. 
    Concise Summaries: When reporting search results, summarize them in one clear, concise sentence.
    Maintain Flow: Avoid ending responses with conversational boilerplate like "Do you have any more questions?" Let the conversation flow naturally.
    Pronunciation: Pronounce numbers naturally (e.g., "two-hundred-fifty," not "two five zero").
    5. FEW-SHOT EXAMPLES:
    Example 1: Leaky Faucet
    USER PROMPT (Audio + Video): (User points the camera at a dripping kitchen faucet) "Ugh, this thing has been dripping for days. What should I do?"
    Lanturn (Ideal Response): "I see the leak from your faucet. First, for safety, turn off the water supply using the small valves under the sink. It's likely a worn-out O-ring. I can walk you through how to replace it if you'd like."
    Example 2: Power Tool Question (Missing Detail)
    USER PROMPT (Audio): "How do I make a pocket hole?"
    Lanturn (Ideal Response): "Of course. To make a pocket hole, you'll need a specialized pocket hole jig. Do you have one, and could you tell me what brand it is? The setup can vary slightly between models."
    Example 3: Weather Inquiry    
    USER PROMPT (Audio): "What's the weather in Tokyo?"
    Lanturn (Ideal Response): "The weather in Tokyo is sunny and 70 degrees Fahrenheit. The humidity is 50%."

    You can use the search_tool to access information from the Google Search API.
    You can SEE what the camera is showing you through the video stream at 1 FPS.
    When the user asks about what you see, describe it clearly and helpfully.
    You can also hear and respond to voice input.
    
    Your output will be converted to audio so don't include special characters in your answers.
    Respond to what the user said in a creative, helpful, and engaging way.
    Keep your responses concise since you're running on a small device.
    """

    llm = GeminiLiveLLMService(
        api_key=os.getenv("GEMINI_API_KEY"),
        system_instruction=system_instruction,
        voice_id="Puck",  # Aoede, Charon, Fenrir, Kore, Puck
    )

    # Create context for managing conversation
    context = OpenAILLMContext(
        [
            {
                "role": "user",
                "content": "Greet the user and introduce yourself as Lantern, an AI with vision running on their ESP32 camera device.",
            },
        ],
    )
    context_aggregator = llm.create_context_aggregator(context)

    # Build the pipeline with context aggregation
    pipeline = Pipeline(
        [
            transport.input(),
            context_aggregator.user(),
            llm,
            transport.output(),
            context_aggregator.assistant(),
        ]
    )

    # Configure the pipeline task
    task = PipelineTask(
        pipeline,
        params=PipelineParams(
            enable_metrics=True,
            enable_usage_metrics=True,
        ),
        idle_timeout_secs=runner_args.pipeline_idle_timeout_secs,
    )

    # Handle client connection event
    @transport.event_handler("on_client_connected")
    async def on_client_connected(transport, client):
        logger.info(f"ESP32 client connected: {client}")
        
        # Capture video from the ESP32 at 1 FPS (Gemini Live's native processing rate)
        await maybe_capture_participant_camera(transport, client, framerate=1)
        
        # Start the conversation
        await task.queue_frames([LLMRunFrame()])
        
        # Give the connection time to stabilize before unpausing
        await asyncio.sleep(3)
        
        # Unpause audio and video input
        logger.info("Unpausing audio and video input")
        llm.set_audio_input_paused(False)
        llm.set_video_input_paused(False)

    # Handle client disconnection events
    @transport.event_handler("on_client_disconnected")
    async def on_client_disconnected(transport, client):
        logger.info(f"ESP32 client disconnected")
        await task.cancel()

    # Run the pipeline
    runner = PipelineRunner(handle_sigint=runner_args.handle_sigint)
    await runner.run(task)


async def bot(runner_args: RunnerArguments):
    """Main bot entry point compatible with Pipecat Cloud."""
    transport = await create_transport(runner_args, transport_params)
    await run_bot(transport, runner_args)


if __name__ == "__main__":
    from pipecat.runner.run import main

    main()

