document.addEventListener('DOMContentLoaded', function () {
  const chatContainer = document.getElementById('chat-container');
  const inputBox = document.getElementById('message-input');
  const sendButton = document.getElementById('send-button');
  const threadId = new URLSearchParams(window.location.search).get('thread_id');

// Modify appendMessage to add classes for styling
function appendMessage(message, isUser) {
  const messageText = message.content[0].text.value;
  const messageDiv = document.createElement('div');
  messageDiv.textContent = messageText;
  
  // Add general message class and conditional class based on the message sender
  messageDiv.classList.add('message');
  messageDiv.classList.add(isUser ? 'user-message' : 'assistant-message');
  
  chatContainer.appendChild(messageDiv);
}
  // Function to load messages from the thread
  async function loadMessages() {
    console.log(`Loading messages for thread: ${threadId}`); // Log the thread ID being queried
    const response = await fetch(`http://127.0.0.1:8000/api/messages/${threadId}`);
    console.log('Response:', response); // Log the raw response
    if (response.ok) {
      const messages = await response.json();
      console.log('Messages received:', messages); // Log the messages received
      chatContainer.innerHTML = ''; // Clear chat container before loading new messages
      messages.forEach(message => {
        const isUser = message.role === 'user';
        appendMessage(message, isUser);
      });
      chatContainer.scrollTop = chatContainer.scrollHeight; // Scroll to the bottom of the chat
    } else {
      console.error('Failed to load messages:', response.statusText); // Log any errors
    }
  }
// Function to post a new message to the thread
async function sendChatMessage() {
  const content = inputBox.value.trim();
  if (!content) return;

  try {
    const response = await fetch(`http://127.0.0.1:8000/api/messages/`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({
        thread_id: threadId,
        content: content,
      })
    });

    if (response.ok) {
      inputBox.value = '';
      loadMessages(); // Reload messages to include the new one
    } else {
      const errorData = await response.json();
      console.error('Failed to send message:', errorData.detail);
    }
  } catch (error) {
    console.error('Failed to send message:', error);
  }
}

  // Event listener for the input box to send message on Enter key press
  inputBox.addEventListener('keypress', function (e) {
    if (e.key === 'Enter') {
      sendChatMessage();
    }
  });

  // Event listener for the send button
  sendButton.addEventListener('click', sendChatMessage);

  // Load messages for the first time
  loadMessages();

  // Set up polling to refresh messages 
  setInterval(loadMessages, 1250);
});
