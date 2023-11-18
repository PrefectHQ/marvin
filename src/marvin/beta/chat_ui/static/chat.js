document.addEventListener('DOMContentLoaded', function () {
  const chatContainer = document.getElementById('chat-container');
  const inputBox = document.getElementById('message-input');
  const sendButton = document.getElementById('send-button');
  const queryParams = new URLSearchParams(window.location.search);
  const threadId = queryParams.get('thread_id');

  // Set the thread ID in the div
  const threadIdDisplay = document.getElementById('thread-id');
  if (threadId) {
    threadIdDisplay.textContent = `Thread ID: ${threadId}`;
  } else {
    threadIdDisplay.textContent = 'No thread ID provided';
  }

  // Extract the port from the URL
  const url = new URL(window.location.href);
  const serverPort = url.port || '8000';  // Default to 8000 if port is not present

  // Modify appendMessage to add classes for styling
  function appendMessage(message, isUser) {
    let messageText = message.content[0].text.value;
    if (messageText === '') {
      messageText = '...';  // Replace blank messages with '...'
    }
    // Use marked to parse Markdown into HTML
    const parsedText = marked.parse(messageText);
  
    const messageDiv = document.createElement('div');
    messageDiv.innerHTML = parsedText; // Use innerHTML since parsedText is HTML
  
    // Add general message class and conditional class based on the message sender
    messageDiv.classList.add('message');
    messageDiv.classList.add(isUser ? 'user-message' : 'assistant-message');
  
    chatContainer.appendChild(messageDiv);
  }
  // Function to load messages from the thread
  async function loadMessages() {
    const response = await fetch(`http://127.0.0.1:${serverPort}/api/messages/`);
    if (response.ok) {
      const messages = await response.json();
      chatContainer.innerHTML = ''; // Clear chat container before loading new messages
      messages.forEach(message => {
        const isUser = message.role === 'user';
        appendMessage(message, isUser);
      });
      chatContainer.scrollTop = chatContainer.scrollHeight; // Scroll to the bottom of the chat
    } else {
      console.error('Failed to load messages:', response.statusText);
    }
  }

  // Function to post a new message to the thread
  async function sendChatMessage() {
    const content = inputBox.value.trim();
    if (!content) return;

    const response = await fetch(`http://127.0.0.1:${serverPort}/api/messages/`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ content: content })
    });

    console.log(response)

    if (response.ok) {
      inputBox.value = '';
      loadMessages();
    } else {
      console.error('Failed to send message:', await response.json());
    }
  }

  // Event listeners
  inputBox.addEventListener('keypress', function (e) {
    if (e.key === 'Enter') {
      sendChatMessage();
    }
  });
  sendButton.addEventListener('click', sendChatMessage);

  // Initial loading of messages
  loadMessages();
  setInterval(loadMessages, 1250); // Polling to refresh messages
});
