// Real-Time Task Monitor JavaScript

document.addEventListener('DOMContentLoaded', function() {
    // Initialize SSE connection
    initializeSSE();
    
    // Clear form after successful submission
    document.body.addEventListener('htmx:afterRequest', function(event) {
        if (event.detail.successful && event.detail.xhr.status === 200) {
            const form = event.target.closest('form');
            if (form) {
                form.reset();
            }
        }
    });
});

function initializeSSE() {
    const connectionStatus = document.getElementById('connection-status');
    
    // Establish SSE connection
    const eventSource = new EventSource('/events');
    
    eventSource.onopen = function() {
        updateConnectionStatus(true);
    };
    
    eventSource.onmessage = function(event) {
        try {
            const data = JSON.parse(event.data);
            handleSSEEvent(data);
        } catch (error) {
            console.log('Received non-JSON message:', event.data);
        }
    };
    
    eventSource.onerror = function(error) {
        console.error('SSE connection error:', error);
        updateConnectionStatus(false);
        
        // Attempt to reconnect after 3 seconds
        setTimeout(() => {
            initializeSSE();
        }, 3000);
    };
    
    // Handle page unload
    window.addEventListener('beforeunload', function() {
        eventSource.close();
    });
}

function handleSSEEvent(data) {
    console.log('Received SSE event:', data);
    
    switch(data.type) {
        case 'activity':
            addActivityMessage(data.data);
            break;
        case 'system_metrics':
            updateSystemMetrics(data.data);
            break;
        case 'task_update':
            // Don't refresh task list via SSE - HTMX handles updates properly
            // The activity feed will still show the task changes
            break;
        case 'heartbeat':
            // Keep connection alive
            break;
        default:
            console.log('Unknown event type:', data.type);
    }
}

function addActivityMessage(activityData) {
    const activityFeed = document.getElementById('activity-feed');
    const timestamp = new Date(activityData.timestamp).toLocaleTimeString();
    
    // Create new activity item
    const activityItem = document.createElement('div');
    activityItem.className = 'activity-item';
    activityItem.innerHTML = `
        <div>${activityData.message}</div>
        <div class="timestamp">${timestamp}</div>
    `;
    
    // Remove "waiting for activity" message if it exists
    const waitingMessage = activityFeed.querySelector('.text-muted.text-center');
    if (waitingMessage) {
        waitingMessage.remove();
    }
    
    // Add to top of feed
    activityFeed.insertBefore(activityItem, activityFeed.firstChild);
    
    // Limit to 10 messages
    const items = activityFeed.querySelectorAll('.activity-item');
    if (items.length > 10) {
        items[items.length - 1].remove();
    }
}

function updateSystemMetrics(metrics) {
    console.log('Updating system metrics:', metrics);
    const cpuElement = document.getElementById('cpu-percent');
    const memoryElement = document.getElementById('memory-percent');
    
    if (cpuElement && memoryElement) {
        cpuElement.textContent = metrics.cpu_percent.toFixed(1) + '%';
        memoryElement.textContent = metrics.memory_percent.toFixed(1) + '%';
        
        // Add visual feedback for high usage
        cpuElement.className = 'h4 mb-0 ' + (metrics.cpu_percent > 80 ? 'text-danger' : 'text-primary');
        memoryElement.className = 'h4 mb-0 ' + (metrics.memory_percent > 80 ? 'text-danger' : 'text-success');
    } else {
        console.error('Could not find CPU or memory elements');
    }
}

function updateConnectionStatus(connected) {
    const statusElement = document.getElementById('connection-status');
    if (statusElement) {
        if (connected) {
            statusElement.innerHTML = '<i class="bi bi-wifi"></i> Connected';
            statusElement.className = 'badge bg-success me-2';
        } else {
            statusElement.innerHTML = '<i class="bi bi-wifi-off"></i> Disconnected';
            statusElement.className = 'badge bg-danger me-2';
        }
    }
}

function updateTaskCount() {
    // Update task count after task operations
    setTimeout(() => {
        const taskItems = document.querySelectorAll('.task-item');
        const taskCountElement = document.getElementById('task-count');
        if (taskCountElement) {
            const count = taskItems.length;
            taskCountElement.textContent = `${count} task${count !== 1 ? 's' : ''}`;
        }
    }, 100);
}

function refreshTaskList() {
    // Fetch and update the task list when receiving SSE updates
    fetch('/tasks')
        .then(response => response.text())
        .then(html => {
            const taskListContainer = document.getElementById('task-list');
            if (taskListContainer) {
                taskListContainer.outerHTML = html;
                updateTaskCount();
                
                // Add highlight animation to show update
                const newTaskList = document.getElementById('task-list');
                if (newTaskList) {
                    newTaskList.classList.add('updated');
                    setTimeout(() => newTaskList.classList.remove('updated'), 1000);
                    
                    // Process HTMX attributes on the new elements
                    htmx.process(newTaskList);
                }
            }
        })
        .catch(error => {
            console.error('Error refreshing task list:', error);
        });
}

// HTMX event handlers
document.body.addEventListener('htmx:beforeRequest', function(event) {
    // Add loading state to buttons
    const button = event.target.closest('button');
    if (button) {
        button.disabled = true;
        const originalText = button.innerHTML;
        button.innerHTML = '<span class="spinner-border spinner-border-sm me-1"></span>Loading...';
        
        // Restore button after request
        event.target.addEventListener('htmx:afterRequest', function() {
            button.disabled = false;
            button.innerHTML = originalText;
        }, { once: true });
    }
});

document.body.addEventListener('htmx:afterSwap', function(event) {
    // Update task count after DOM changes
    updateTaskCount();
    
    // Add highlight animation to updated elements
    const target = event.target;
    if (target.id === 'task-list') {
        target.classList.add('updated');
        setTimeout(() => target.classList.remove('updated'), 1000);
    }
});