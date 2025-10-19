from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters, ContextTypes
import google.generativeai as genai
import logging

# Configure logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)

# Configuration
TELEGRAM_BOT_TOKEN = "YOUR_TELEGRAM_BOT_TOKEN_HERE"
GEMINI_API_KEY = "YOUR_GEMINI_API_KEY_HERE"

# Configure Gemini AI
genai.configure(api_key=GEMINI_API_KEY)
model = genai.GenerativeModel('gemini-1.5-flash')

# Store conversation history for each user
conversation_history = {}

def generate_academic_response(user_id: int, user_message: str) -> str:
    """Generate academic-focused responses using Gemini AI"""
    try:
        # Initialize conversation history for new users
        if user_id not in conversation_history:
            conversation_history[user_id] = []
        
        # Add system prompt for academic context
        system_prompt = """You are an academic assistant bot. Your role is to:
        - Help students with homework, assignments, and research
        - Explain complex academic concepts clearly
        - Provide study tips and learning strategies
        - Answer questions across various subjects
        - Encourage critical thinking
        Keep responses educational, clear, and helpful."""
        
        # Build conversation context
        full_prompt = f"{system_prompt}\n\nUser: {user_message}"
        
        # Add conversation history for context
        if conversation_history[user_id]:
            history_context = "\n".join([
                f"User: {msg['user']}\nAssistant: {msg['bot']}" 
                for msg in conversation_history[user_id][-3:]  # Last 3 exchanges
            ])
            full_prompt = f"{system_prompt}\n\nPrevious conversation:\n{history_context}\n\nUser: {user_message}"
        
        # Generate response
        response = model.generate_content(full_prompt)
        response_text = response.text if hasattr(response, 'text') else "Sorry, I couldn't generate a response."
        
        # Store in history
        conversation_history[user_id].append({
            'user': user_message,
            'bot': response_text
        })
        
        # Keep only last 10 exchanges
        if len(conversation_history[user_id]) > 10:
            conversation_history[user_id] = conversation_history[user_id][-10:]
        
        return response_text
        
    except Exception as e:
        logging.error(f"Error generating response: {str(e)}")
        return f"⚠ Error: {str(e)}\nPlease try again later."

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /start command"""
    user_name = update.effective_user.first_name
    welcome_message = f"""👋 Hello {user_name}! 

I'm your Academic Assistant Bot powered by Gemini AI.

I can help you with:
📚 Homework and assignments
🔬 Science, Math, and all subjects
💡 Explaining complex concepts
📖 Study strategies and tips
✍ Research and writing help

Just send me your question and I'll do my best to help!

Commands:
/start - Show this welcome message
/help - Get help information
/new - Start a new conversation
/clear - Clear conversation history"""
    
    await update.message.reply_text(welcome_message)

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /help command"""
    help_text = """🤖 Academic Bot Help

How to use:
• Simply type your question or topic
• I'll provide detailed academic explanations
• Ask follow-up questions for clarification

Examples:
"Explain photosynthesis"
"Help me solve quadratic equations"
"What is machine learning?"
"Tips for writing essays"

Commands:
/start - Welcome message
/help - This help message
/new - Start fresh conversation
/clear - Clear history"""
    
    await update.message.reply_text(help_text)

async def new_conversation(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /new command - start new conversation"""
    user_id = update.effective_user.id
    if user_id in conversation_history:
        conversation_history[user_id] = []
    await update.message.reply_text("✨ New conversation started! What would you like to learn about?")

async def clear_history(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /clear command - clear conversation history"""
    user_id = update.effective_user.id
    if user_id in conversation_history:
        conversation_history[user_id] = []
    await update.message.reply_text("🗑 Conversation history cleared!")

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle incoming text messages"""
    user_id = update.effective_user.id
    user_message = update.message.text
    
    # Show typing indicator
    await update.message.chat.send_action(action="typing")
    
    # Generate and send response
    response_text = generate_academic_response(user_id, user_message)
    await update.message.reply_text(response_text)

async def handle_photo(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle photos with optional captions (multimodal)"""
    try:
        # Get the photo
        photo = update.message.photo[-1]  # Get highest resolution
        photo_file = await photo.get_file()
        photo_path = f"temp_{update.effective_user.id}.jpg"
        await photo_file.download_to_drive(photo_path)
        
        # Get caption if available
        caption = update.message.caption or "What's in this image?"
        
        # Use Gemini Pro Vision for image analysis
        vision_model = genai.GenerativeModel('gemini-1.5-flash')
        
        # Read image file
        import PIL.Image
        img = PIL.Image.open(photo_path)
        
        # Generate response with image
        prompt = f"Academic context: {caption}"
        response = vision_model.generate_content([prompt, img])
        
        await update.message.reply_text(response.text)
        
        # Clean up temp file
        import os
        os.remove(photo_path)
        
    except Exception as e:
        logging.error(f"Error processing image: {str(e)}")
        await update.message.reply_text("Sorry, I couldn't process the image. Please try again.")

def main():
    """Start the bot"""
    # Build application
    app = ApplicationBuilder().token(TELEGRAM_BOT_TOKEN).build()
    
    # Add command handlers
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("help", help_command))
    app.add_handler(CommandHandler("new", new_conversation))
    app.add_handler(CommandHandler("clear", clear_history))
    
    # Add message handlers
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    app.add_handler(MessageHandler(filters.PHOTO, handle_photo))
    
    # Start polling
    logging.info("Bot started successfully!")
    app.run_polling()

if __name__ == "_main_":
    main()