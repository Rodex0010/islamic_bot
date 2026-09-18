async def safe_edit_or_reply(query, text, parse_mode="HTML", reply_markup=None):
    """تعديل أو إرسال رسالة بشكل آمن بدون Errors"""

    # متبعتش نص فاضي
    if not text or not text.strip():
        return

    try:
        # نحاول نعدل الرسالة
        await query.edit_message_text(
            text=text,
            parse_mode=parse_mode,
            reply_markup=reply_markup
        )
    except Exception:
        try:
            # لو التعديل فشل، نرد على الرسالة
            if query.message:
                await query.message.reply_text(
                    text=text,
                    parse_mode=parse_mode,
                    reply_markup=reply_markup
                )
        except Exception:
            try:
                # fallback أخير
                await query.bot.send_message(
                    chat_id=query.message.chat_id,
                    text=text,
                    parse_mode=parse_mode,
                    reply_markup=reply_markup
                )
            except Exception as e:
                print(f"❌ Failed to send message: {e}")