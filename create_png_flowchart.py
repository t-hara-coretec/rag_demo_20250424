import matplotlib.pyplot as plt
import matplotlib.patches as patches
import numpy as np

# Create a figure and axis
fig, ax = plt.subplots(figsize=(14, 9))

# Define colors
colors = {
    'blue': '#2374ab',
    'green': '#1aa555',
    'orange': '#ff7700',
    'purple': '#673ab7',
    'red': '#cc3311',
    'gray': '#555555'
}

# Define boxes with their positions, sizes, colors, and labels
def add_box(x, y, width, height, color, label, ax):
    box = patches.Rectangle((x, y), width, height, linewidth=1, edgecolor=color, facecolor=color, alpha=0.7)
    ax.add_patch(box)
    ax.text(x + width/2, y + height/2, label, ha='center', va='center', color='white', fontweight='bold', wrap=True)

# Define arrows
def add_arrow(start_x, start_y, end_x, end_y, color, label, ax):
    ax.annotate('', xy=(end_x, end_y), xytext=(start_x, start_y),
                arrowprops=dict(arrowstyle='->', lw=1.5, color=color))
    
    # Calculate the midpoint for the label
    mid_x = (start_x + end_x) / 2
    mid_y = (start_y + end_y) / 2
    
    # Add a small offset to avoid overlapping with the arrow
    offset = 0.1
    if abs(end_x - start_x) > abs(end_y - start_y):
        mid_y += offset
    else:
        mid_x += offset
        
    ax.text(mid_x, mid_y, label, ha='center', va='center', color=color, fontsize=8, 
            bbox=dict(facecolor='white', alpha=0.7, boxstyle='round,pad=0.2'))

# Define the components
# Frontend
add_box(2, 7, 2, 1, colors['blue'], 'User', ax)
add_box(2, 5, 2, 1, colors['blue'], 'Web Interface\n(chat_app.html/ts)', ax)

# Backend
add_box(2, 3, 2, 1, colors['orange'], 'FastAPI Backend\n(chat_app.py)', ax)
add_box(0, 1, 1.5, 1, colors['purple'], 'SQLite\nDatabase', ax)
add_box(8, 3, 2, 1, colors['red'], 'Language Model\n(OpenAI/Ollama)', ax)

# RAG components
add_box(4, 1, 2, 1, colors['green'], 'RAG Service\n(rag_service.py)', ax)
add_box(2, 1, 1.5, 1, colors['green'], 'Vector Store\n(vector_store.py)', ax)
add_box(5.5, 1, 1.5, 1, colors['green'], 'Web Processor\n(web_processor.py)', ax)
add_box(0, -1, 1.5, 1, colors['green'], 'PDF Processor\n(pdf_processor.py)', ax)
add_box(4, -1, 2, 1, colors['purple'], 'ChromaDB\nVector Database', ax)
add_box(0, -3, 1.5, 1, colors['purple'], 'PDF Documents', ax)
add_box(5.5, -1, 1.5, 1, colors['purple'], 'Web Content', ax)

# Add arrows
# User flow
add_arrow(3, 7, 3, 6, colors['gray'], '1. Sends query', ax)
add_arrow(3, 5, 3, 4, colors['gray'], '2. HTTP request', ax)

# Backend flows
add_arrow(2, 3, 1, 2, colors['gray'], '3b. Store messages', ax)
add_arrow(4, 3, 5, 2, colors['gray'], '3a. If RAG enabled', ax)
add_arrow(4, 3, 8, 3.5, colors['gray'], '4. Query LLM', ax)
add_arrow(8, 3, 4, 3, colors['gray'], '5. Response', ax)
add_arrow(3, 3, 3, 5, colors['gray'], '6. Stream response', ax)

# RAG flows
add_arrow(4, 1, 3.5, 1, colors['gray'], 'Get docs', ax)
add_arrow(2.75, 1, 2.75, 0, colors['gray'], 'Process PDFs', ax)
add_arrow(5, 1, 5, 0, colors['gray'], 'Vector search', ax)
add_arrow(6.25, 1, 6.25, 0, colors['gray'], 'Fetch & cache', ax)
add_arrow(0.75, 0, 0.75, -2, colors['gray'], 'Read', ax)

# Set up axis limits
ax.set_xlim(-0.5, 11)
ax.set_ylim(-3.5, 8.5)

# Remove axis ticks and labels
ax.set_xticks([])
ax.set_yticks([])

# Add title
ax.set_title('RAG Demo Project - Flow Chart')

# Remove axis spines
for spine in ax.spines.values():
    spine.set_visible(False)

# Save the figure
plt.tight_layout()
plt.savefig('rag_flowchart.png', dpi=150, bbox_inches='tight')
plt.close()