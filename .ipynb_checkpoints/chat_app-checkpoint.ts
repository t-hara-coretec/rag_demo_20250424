import { marked } from 'https://cdnjs.cloudflare.com/ajax/libs/marked/15.0.0/lib/marked.esm.js'
const convElement = document.getElementById('conversation')

const promptInput = document.getElementById('prompt-input') as HTMLInputElement
const useRagCheckbox = document.getElementById('use-rag') as HTMLInputElement
const spinner = document.getElementById('spinner')
const clearBtn = document.getElementById('clear-btn') as HTMLButtonElement
const urlForm = document.getElementById('url-form') as HTMLFormElement
const urlInput = document.getElementById('url-input') as HTMLInputElement
const urlStatus = document.getElementById('url-status') as HTMLDivElement

// stream the response and render messages as each chunk is received
// data is sent as newline-delimited JSON
async function onFetchResponse(response: Response): Promise<void> {
  let text = ''
  let decoder = new TextDecoder()
  if (response.ok) {
    const reader = response.body.getReader()
    while (true) {
      const {done, value} = await reader.read()
      if (done) {
        break
      }
      text += decoder.decode(value)
      addMessages(text)
      spinner.classList.remove('active')
    }
    addMessages(text)
    promptInput.disabled = false
    promptInput.focus()
  } else {
    const text = await response.text()
    console.error(`Unexpected response: ${response.status}`, {response, text})
    throw new Error(`Unexpected response: ${response.status}`)
  }
}

// The format of messages, this matches pydantic-ai both for brevity and understanding
// in production, you might not want to keep this format all the way to the frontend
interface Message {
  role: string
  content: string
  timestamp: string
}

// Helper function to scroll conversation to bottom
function scrollConversationToBottom(delay = 0) {
  setTimeout(() => {
    if (convElement) {
      convElement.scrollTop = convElement.scrollHeight;
    }
  }, delay);
}

// take raw response text and render messages into the `#conversation` element
// Message timestamp is assumed to be a unique identifier of a message, and is used to deduplicate
// hence you can send data about the same message multiple times, and it will be updated
// instead of creating a new message elements
function addMessages(responseText: string) {
  const lines = responseText.split('\n')
  const messages: Message[] = lines.filter(line => line.length > 1).map(j => JSON.parse(j))
  
  // Clear the 'Ask me anything...' message if we have messages to display
  if (messages.length > 0) {
    const welcomeMsg = convElement.querySelector('p.text-muted')
    if (welcomeMsg) {
      welcomeMsg.remove()
    }
  }
  
  // Remove any client-side added messages from previous submissions 
  // (they'll be replaced by server-sent ones)
  const clientSideMessages = convElement.querySelectorAll('[data-client-side="true"]');
  clientSideMessages.forEach(msg => msg.remove());
  
  for (const message of messages) {
    // we use the timestamp as a crude element id
    const {timestamp, role, content} = message
    const id = `msg-${timestamp}`
    let msgDiv = document.getElementById(id)
    if (!msgDiv) {
      msgDiv = document.createElement('div')
      msgDiv.id = id
      msgDiv.title = `${role} at ${timestamp}`
      msgDiv.classList.add('border-top', 'pt-2', role)
      convElement.appendChild(msgDiv)
    }
    msgDiv.innerHTML = marked.parse(content)
  }
  // Scroll the conversation container to the bottom to show the latest message
  scrollConversationToBottom(0);
}

function onError(error: any) {
  console.error(error)
  document.getElementById('error').classList.remove('d-none')
  document.getElementById('spinner').classList.remove('active')
}

async function onSubmit(e: SubmitEvent): Promise<void> {
  e.preventDefault();
  spinner.classList.add('active');
  const body = new FormData(e.target as HTMLFormElement);
  
  // Make sure the useRag checkbox value is properly set in the form data
  // FormData.set will ensure the correct value is sent
  body.set('use_rag', useRagCheckbox.checked ? 'true' : 'false');

  // First create a user message div to immediately show what the user submitted
  // We'll add a temporary attribute to identify this as a client-side message
  const userPrompt = body.get('prompt') as string;
  if (userPrompt && userPrompt.trim()) {
    const timestamp = new Date().toISOString();
    const userDiv = document.createElement('div');
    userDiv.id = `msg-${timestamp}`;
    userDiv.title = `user at ${timestamp}`;
    userDiv.classList.add('border-top', 'pt-2', 'user');
    userDiv.dataset.clientSide = 'true'; // Add a data attribute to mark this as a client-side message
    userDiv.innerHTML = marked.parse(userPrompt);
    convElement.appendChild(userDiv);
    
    // Scroll to show the user message immediately
    scrollConversationToBottom(0);
    
    // Store the timestamp to check for duplicates later
    body.append('client_timestamp', timestamp);
  }

  promptInput.value = '';
  promptInput.disabled = true;

  const response = await fetch('/chat/', {method: 'POST', body});
  await onFetchResponse(response);
}

async function clearConversation(): Promise<void> {
  if (confirm('Are you sure you want to clear the conversation history?')) {
    spinner.classList.add('active')
    try {
      const response = await fetch('/chat/clear', {method: 'POST'})
      if (response.ok) {
        // Clear the conversation display and restore welcome message
        convElement.innerHTML = `
          <div class="text-center py-5">
            <div class="bg-primary rounded-circle d-inline-flex justify-content-center align-items-center mb-3" style="width: 60px; height: 60px;">
              <span class="fw-bold text-white fs-4">AI</span>
            </div>
            <h4>Welcome to the Chat App</h4>
            <p class="text-muted">Ask me anything...</p>
          </div>
        `
        
        // Show success message
        const successMsg = document.createElement('div')
        successMsg.classList.add('alert', 'alert-success', 'mt-3')
        successMsg.textContent = 'Conversation history cleared successfully!'
        convElement.appendChild(successMsg)
        
        // Scroll to show the success message
        scrollConversationToBottom(0);
        
        // Auto-remove the success message after 3 seconds
        setTimeout(() => {
          successMsg.remove()
          // Scroll after removing the message to ensure proper positioning
          scrollConversationToBottom(0);
        }, 3000)
      } else {
        throw new Error(`Failed to clear history: ${response.status}`)
      }
    } catch (error) {
      console.error('Error clearing conversation:', error)
      document.getElementById('error').classList.remove('d-none')
    } finally {
      spinner.classList.remove('active')
    }
  }
}

// Handle URL form submission to add web content to knowledge base
async function handleUrlSubmit(e: SubmitEvent): Promise<void> {
  e.preventDefault();
  
  // Show loading state
  const submitBtn = urlForm.querySelector('button');
  const originalBtnText = submitBtn.innerHTML;
  submitBtn.disabled = true;
  submitBtn.innerHTML = 'Adding...';
  
  // Show status area
  urlStatus.classList.remove('d-none');
  urlStatus.innerHTML = 'Processing URL...';
  urlStatus.className = 'small mt-2 text-info';
  
  try {
    const url = urlInput.value.trim();
    console.log('Submitting URL:', url);
    
    // Create form data with URL
    const formData = new FormData();
    formData.append('url', url);
    
    // Log form data for debugging
    console.log('FormData entries:');
    for (let pair of formData.entries()) {
      console.log(pair[0] + ': ' + pair[1]);
    }
    
    // Send request to add URL
    const response = await fetch('/add_url/', {
      method: 'POST',
      body: formData
    });
    
    console.log('Response status:', response.status);
    
    const responseText = await response.text();
    console.log('Raw response:', responseText);
    
    let result;
    try {
      // Try to parse as JSON
      result = JSON.parse(responseText);
    } catch (e) {
      console.error('Failed to parse response as JSON:', e);
      throw new Error('Invalid response format from server');
    }
    
    if (response.ok) {
      // Show success message
      urlStatus.innerHTML = `✓ ${result.message}`;
      urlStatus.className = 'small mt-2 text-success';
      
      // Clear input field
      urlInput.value = '';
      
      // Refresh the URL list
      fetchURLs().catch(e => console.error('Error refreshing URLs after add:', e));
    } else {
      throw new Error(result.message || `Server error: ${response.status}`);
    }
  } catch (error) {
    console.error('Error adding URL:', error);
    urlStatus.innerHTML = `✗ ${error.message || 'Failed to add URL'}`;
    urlStatus.className = 'small mt-2 text-danger';
  } finally {
    // Restore button state
    submitBtn.disabled = false;
    submitBtn.innerHTML = originalBtnText;
    
    // Hide status after a delay on success
    setTimeout(() => {
      if (urlStatus.classList.contains('text-success')) {
        urlStatus.classList.add('d-none');
      }
    }, 5000);
  }
}

// call onSubmit when the form is submitted (e.g. user clicks the send button or hits Enter)
document.querySelector('form[method="post"]').addEventListener('submit', (e) => onSubmit(e).catch(onError))

// Add event listener for clear button
clearBtn.addEventListener('click', () => clearConversation().catch(onError))

// Add event listener for URL form
urlForm.addEventListener('submit', (e) => handleUrlSubmit(e).catch(onError))

// Add event listener for refresh URLs button
document.getElementById('refresh-urls-btn').addEventListener('click', () => fetchURLs().catch(onError))

// Fetch and display URLs in the list
async function fetchURLs(): Promise<void> {
  try {
    console.log('Fetching URLs from server...');
    const urlList = document.getElementById('url-list')
    
    // Show loading state
    urlList.innerHTML = '<div class="text-muted text-center py-2">Loading URLs...</div>'
    
    // Fetch URLs from backend
    const response = await fetch('/get_urls/')
    console.log('URL fetch response status:', response.status);
    
    if (!response.ok) {
      throw new Error(`Failed to fetch URLs: ${response.status}`)
    }
    
    const responseText = await response.text();
    console.log('Raw response from /get_urls/:', responseText);
    
    let data;
    try {
      data = JSON.parse(responseText);
    } catch (e) {
      console.error('Failed to parse /get_urls/ response as JSON:', e);
      throw new Error('Invalid response format from server');
    }
    
    console.log('Parsed URL data:', data);
    
    if (data.status === 'success') {
      const urls = data.urls
      console.log(`Found ${urls ? urls.length : 0} URLs`);
      
      if (urls && urls.length > 0) {
        // Create HTML for each URL
        const urlItems = urls.map(url => `
          <a href="${url.url}" target="_blank" class="list-group-item list-group-item-action d-flex align-items-center p-2 border-0">
            <span class="text-truncate" title="${url.title}">${url.title}</span>
            <span class="badge bg-secondary ms-auto">${url.domain}</span>
          </a>
        `).join('')
        
        urlList.innerHTML = urlItems
      } else {
        urlList.innerHTML = '<div class="text-muted text-center py-2">No URLs added yet</div>'
      }
    } else {
      throw new Error(data.message || 'Failed to fetch URLs')
    }
  } catch (error) {
    console.error('Error fetching URLs:', error)
    document.getElementById('url-list').innerHTML = `
      <div class="text-danger text-center py-2">
        Failed to load URLs. 
        <button class="btn btn-sm btn-link p-0" onclick="fetchURLs()">Try again</button>
      </div>
    `
  }
}

// Set up a MutationObserver to automatically scroll when new content is added
const conversationObserver = new MutationObserver((mutations) => {
  // Only scroll if content was added (not just attributes changed)
  const contentAdded = mutations.some(mutation => 
    mutation.type === 'childList' && mutation.addedNodes.length > 0
  );
  
  if (contentAdded) {
    scrollConversationToBottom(10); // Small delay to allow DOM to settle
  }
});

// Start observing the conversation area for added/removed nodes
if (convElement) {
  conversationObserver.observe(convElement, { childList: true, subtree: true });
}

// load messages on page load
fetch('/chat/').then(onFetchResponse).then(() => {
  // Ensure conversation is scrolled to the bottom after initial messages are loaded
  scrollConversationToBottom(100); // Slightly longer timeout for initial load
}).catch(onError)

// fetch URLs on page load
fetchURLs().catch(onError)