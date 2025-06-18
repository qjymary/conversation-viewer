import json
import pandas as pd
import streamlit as st
import re

# Title
st.title("Conversation JSON Viewer")

# File uploader or load static Excel
uploaded = st.file_uploader("Upload Excel", type=["xlsx", "xls"])  
if uploaded:
    df = pd.read_excel(uploaded)
else:
    st.info("Please upload an Excel file containing conversation_json.")
    st.stop()

# Select a session to view
session_ids = df['remote_id'].unique().tolist()
selected = st.selectbox("Select remote_id", session_ids)
row = df[df['remote_id'] == selected].iloc[0]

# 获取JSON字符串
raw_json = row['conversation_json']

# Parse JSON directly without complex regex
try:
    # 更简单的方法：直接从原始字符串提取消息
    def extract_messages_direct(json_str):
        # 首先尝试直接解析完整JSON
        try:
            data = json.loads(json_str)
            return data
        except:
            pass
        
        # 失败后，使用分段解析的方法
        messages = []
        
        # 替换转义斜杠，使JSON更易处理 - 修复无效的转义序列
        json_str = json_str.replace('\\/', '/')  # 使用双反斜杠作为转义符
        
        # 从字符串中提取每个消息对象
        # 首先找到所有 "send_type":number 的位置，这标志着每个消息的开始
        # 对于原始字符串，我们可以直接使用暴力方法拆分和处理
        msg_starts = [m.start() for m in re.finditer(r'{"send_type":', json_str)]
        if not msg_starts:
            raise Exception("找不到消息开始标记")
        
        for i in range(len(msg_starts)):
            start_pos = msg_starts[i]
            # 结束位置是下一条消息的开始或字符串结束
            end_pos = msg_starts[i+1] if i < len(msg_starts)-1 else len(json_str)
            
            msg_json = json_str[start_pos:end_pos].rstrip(',')
            
            # 提取基本信息
            send_type_match = re.search(r'"send_type":(\d+)', msg_json)
            create_time_match = re.search(r'"create_time":"([^"]+)"', msg_json)
            
            # 提取msg_type (如果存在)
            msg_type = 0  # 默认为0
            msg_type_match = re.search(r'"msg_type":(\d+)', msg_json)
            if msg_type_match:
                msg_type = int(msg_type_match.group(1))
            
            if send_type_match and create_time_match:
                send_type = int(send_type_match.group(1))
                create_time = create_time_match.group(1)
                
                # 提取msg_content，这是最复杂的部分
                # 找到 "msg_content":" 之后的内容，直到最后一个引号（考虑转义）
                content_start = msg_json.find('"msg_content":"')
                if content_start != -1:
                    content_start += len('"msg_content":"')
                    # 寻找不被转义的最后一个引号
                    content_end = len(msg_json) - 1
                    while content_end > content_start:
                        if msg_json[content_end] == '"' and msg_json[content_end-1] != '\\':
                            break
                        content_end -= 1
                    
                    msg_content = msg_json[content_start:content_end]
                    # 处理转义
                    msg_content = msg_content.replace('\\"', '"')
                    
                    messages.append({
                        'send_type': send_type,
                        'create_time': create_time,
                        'msg_type': msg_type,
                        'msg_content': msg_content
                    })
        
        if messages:
            return messages
        else:
            raise Exception("未能提取任何消息")
    
    # 使用新方法解析对话
    conv = extract_messages_direct(raw_json)
    
except Exception as e:
    st.error(f"JSON parse error: {str(e)}")
    st.write("原始JSON字符串:")
    st.code(raw_json)

    # 尝试显示部分解析结果
    try:
        # 使用最基本的方式尝试展示内容
        st.write("尝试显示可能的对话内容:")
        
        # 找到所有 send_type 和 相应的 msg_content
        user_pattern = r'"send_type":1[^}]*"msg_content":"([^"]*(?:\\"|[^"])*)"'
        assistant_pattern = r'"send_type":0[^}]*"msg_content":"([^"]*(?:\\"|[^"])*)"'
        
        user_matches = re.finditer(user_pattern, raw_json)
        for match in user_matches:
            content = match.group(1).replace('\\"', '"')
            st.write(f"**用户**: {content}")
            
        assistant_matches = re.finditer(assistant_pattern, raw_json)
        for match in assistant_matches:
            content = match.group(1).replace('\\"', '"')
            st.write(f"**助手**: {content}")
            
    except Exception as e:
        st.error(f"备用解析也失败: {str(e)}")
        
    st.stop()

# Display conversation
for msg in conv:
    sender = "User" if msg['send_type'] == 1 else "Assistant"
    timestamp = msg.get('create_time')
    msg_type = msg.get('msg_type', 0)  # 获取消息类型，默认为0
    content = msg.get('msg_content', '')
    
    # 移除前缀
    if content.startswith('user:') or content.startswith('assistant:'):
        prefix, _, content_text = content.partition(':')
        content_display = content_text.strip()
    else:
        content_display = content
    
    # 尝试解析嵌套的JSON内容
    if content_display.strip().startswith('{') and content_display.strip().endswith('}'):
        try:
            parsed_json = json.loads(content_display)
            content_display = json.dumps(parsed_json, indent=2, ensure_ascii=False)
        except:
            # 如果无法解析为JSON，保持原样显示
            pass

    with st.container():
        if sender == "User":
            # 显示包含msg_type的标题
            st.markdown(f"**🧑 User** [{timestamp}] [类型: {msg_type}]: ")
            st.code(content_display, language="json" if content_display.strip().startswith('{') else None)
        else:
            # 显示包含msg_type的标题
            st.markdown(f"**🤖 Assistant** [{timestamp}] [类型: {msg_type}]: ")
            st.write(content_display)

# Footer
st.caption("Rendered by Streamlit JSON chat viewer.")
