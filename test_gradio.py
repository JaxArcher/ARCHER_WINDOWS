#!/usr/bin/env python3
"""
Simple Gradio test for ARCHER Windows
"""

import gradio as gr
import sys
import os

def simple_chat(message, history):
    """Simple echo chatbot for testing"""
    return f"You said: {message}"

def create_simple_interface():
    """Create a simple Gradio interface"""
    with gr.Blocks(title="ARCHER Windows Test") as demo:
        gr.Markdown("# ARCHER Windows - Simple Test Interface")
        gr.Markdown("This is a minimal test to verify Gradio is working.")
        
        chatbot = gr.Chatbot(label="Chat with ARCHER")
        msg = gr.Textbox(label="Type a message...")
        clear = gr.Button("Clear")
        
        def user_input(user_message, history):
            return "", history + [[user_message, None]]
        
        def bot_response(history):
            if history and history[-1][1] is None:
                user_msg = history[-1][0]
                history[-1][1] = simple_chat(user_msg, history)
            return history
        
        msg.submit(user_input, [msg, chatbot], [msg, chatbot]).then(
            bot_response, chatbot, chatbot
        )
        clear.click(lambda: None, None, chatbot, queue=False)
    
    return demo

if __name__ == "__main__":
    print("Starting ARCHER Windows Simple Test...")
    print("Gradio version:", gr.__version__)
    
    demo = create_simple_interface()
    
    try:
        demo.launch(
            server_name="0.0.0.0",
            server_port=7860,
            share=False,
            debug=True
        )
    except Exception as e:
        print(f"Error launching Gradio: {e}")
        sys.exit(1)