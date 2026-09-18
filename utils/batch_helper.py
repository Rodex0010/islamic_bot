# utils/batch_helper.py
# النسخة الكاملة - إرسال لجميع المستخدمين والشاتات

import asyncio
from typing import List, Callable, Any

async def send_batch_messages(
    bot,
    chat_ids: List[int],
    send_func: Callable,
    delay_between_batches: float = 1.5,
    batch_size: int = 10,
    max_retries: int = 3,
    **kwargs
):
    """
    إرسال رسائل لمجموعة كبيرة من المستخدمين على دفعات
    يرسل لجميع الشاتات المحددة
    """
    if not chat_ids:
        return
    
    total = len(chat_ids)
    success_count = 0
    
    for i in range(0, total, batch_size):
        batch = chat_ids[i:i+batch_size]
        
        for chat_id in batch:
            for attempt in range(max_retries):
                try:
                    await send_func(chat_id=chat_id, **kwargs)
                    success_count += 1
                    break
                    
                except Exception as e:
                    error_msg = str(e).lower()
                    
                    if "chat not found" in error_msg or "forbidden" in error_msg or "bot is not a member" in error_msg:
                        from database import remove_active_chat, remove_user
                        remove_active_chat(chat_id)
                        remove_user(chat_id)
                        break
                    
                    elif "interdc" in error_msg or "500" in error_msg or "timeout" in error_msg:
                        if attempt < max_retries - 1:
                            wait_time = 2 ** attempt
                            await asyncio.sleep(wait_time)
                        else:
                            print(f"❌ Failed to send to {chat_id} after {max_retries} attempts")
                    
                    else:
                        break
        
        if i + batch_size < total:
            await asyncio.sleep(delay_between_batches)
    
    print(f"✅ Sent {success_count}/{total} messages")
    return success_count


async def send_batch_audio(
    bot,
    chat_ids: List[int],
    audio_file: str,
    title: str = "",
    delay_between_batches: float = 2.0,
    batch_size: int = 5,
    max_retries: int = 3,
    **kwargs
):
    """
    إرسال ملفات صوتية لمجموعة كبيرة على دفعات
    يرسل لجميع الشاتات المحددة
    """
    if not chat_ids or not audio_file:
        return
    
    total = len(chat_ids)
    success_count = 0
    
    for i in range(0, total, batch_size):
        batch = chat_ids[i:i+batch_size]
        
        for chat_id in batch:
            for attempt in range(max_retries):
                try:
                    await bot.send_audio(
                        chat_id=chat_id,
                        audio=audio_file,
                        title=title,
                        **kwargs
                    )
                    success_count += 1
                    break
                    
                except Exception as e:
                    error_msg = str(e).lower()
                    
                    if "chat not found" in error_msg or "forbidden" in error_msg:
                        from database import remove_active_chat
                        remove_active_chat(chat_id)
                        break
                    
                    elif "interdc" in error_msg or "500" in error_msg or "timeout" in error_msg:
                        if attempt < max_retries - 1:
                            await asyncio.sleep(2 ** attempt)
                        else:
                            print(f"❌ Audio failed for {chat_id}")
                    
                    else:
                        break
        
        if i + batch_size < total:
            await asyncio.sleep(delay_between_batches)
    
    print(f"✅ Sent {success_count}/{total} audio files")
    return success_count


async def send_batch_messages_with_custom_delay(
    bot,
    chat_ids: List[int],
    send_func: Callable,
    delay_between_messages: float = 0.5,
    max_retries: int = 3,
    **kwargs
):
    """
    إرسال رسائل لمجموعة مع تأخير بين كل رسالة وأخرى
    """
    if not chat_ids:
        return
    
    total = len(chat_ids)
    success_count = 0
    
    for chat_id in chat_ids:
        for attempt in range(max_retries):
            try:
                await send_func(chat_id=chat_id, **kwargs)
                success_count += 1
                break
                
            except Exception as e:
                error_msg = str(e).lower()
                
                if "chat not found" in error_msg or "forbidden" in error_msg:
                    from database import remove_active_chat, remove_user
                    remove_active_chat(chat_id)
                    remove_user(chat_id)
                    break
                
                elif "interdc" in error_msg or "500" in error_msg or "timeout" in error_msg:
                    if attempt < max_retries - 1:
                        await asyncio.sleep(2 ** attempt)
                    else:
                        print(f"❌ Failed to send to {chat_id} after {max_retries} attempts")
                
                else:
                    break
        
        await asyncio.sleep(delay_between_messages)
    
    print(f"✅ Sent {success_count}/{total} messages")
    return success_count