<template>
  <div class="bg-animation"></div>
  <div id="app">
    <main class="main-layout">
      <section class="premium-card">
        <header>
          <h1>Magic Designer</h1>
          <p class="subtitle">Turn raw ideas into cinematic decks in seconds.</p>
        </header>

        <form @submit.prevent="handleSubmit">
          <!-- Multi-Mode Ingestion -->
          <div class="ingestion-tabs">
            <button 
              type="button" 
              class="tab-btn" 
              :class="{ active: inputMode === 'file' }"
              @click="inputMode = 'file'"
            >📄 Document</button>
            <button 
              type="button" 
              class="tab-btn" 
              :class="{ active: inputMode === 'text' }"
              @click="inputMode = 'text'"
            >✍️ Manual Text</button>
          </div>

          <!-- File Mode -->
          <div v-if="inputMode === 'file'" class="form-group">
            <div 
              class="cinematic-dropzone"
              :class="{ 'dragging': isDragging }"
              @click="triggerFileInput"
              @dragover.prevent="isDragging = true"
              @dragleave.prevent="isDragging = false"
              @drop.prevent="handleFileDrop"
            >
              <input ref="fileInput" type="file" hidden @change="handleFileSelect" accept=".pdf,.docx,.txt" />
              <div v-if="!selectedFile">
                <div class="drop-icon">📂</div>
                <p class="drop-text">Drop your PDF, Word, or Text file</p>
                <small class="drop-hint">AI will extract and design your slides</small>
              </div>
              <div v-else class="file-info">
                <div class="file-icon">📄</div>
                <p class="file-name">{{ selectedFile.name }}</p>
                <button type="button" @click.stop="clearFile" class="btn-clear">Choose Another</button>
              </div>
            </div>
          </div>

          <!-- Text Mode -->
          <div v-else class="form-group">
            <textarea 
              v-model="htmlContent" 
              class="premium-textarea" 
              placeholder="e.g.&#10;1. Introduction to AI in 2024&#10;2. The rise of Agentic Workflow&#10;3. Future of Human-AI Collaboration...&#10;&#10;AI will transform each point into a professional slide."
              rows="8"
              :required="inputMode === 'text'"
            ></textarea>
          </div>

          <button type="submit" class="btn-generate" :disabled="isLoading || (inputMode === 'text' && !htmlContent) || (inputMode === 'file' && !selectedFile)" style="margin-top: 2rem;">
            <span v-if="!isLoading">🚀 Design Cinematic Deck</span>
            <span v-else>✨ {{ currentProgress || 'Extracting & Designing...' }}</span>
          </button>
        </form>

        <!-- Progress Feedback Section -->
        <div v-if="isLoading" class="progress-container">
          <div class="progress-bar">
            <div class="progress-fill"></div>
          </div>
          <p class="progress-status">{{ currentProgress }}</p>
          <button 
            type="button" 
            class="btn-cancel" 
            @click="handleCancel"
          >
            ⏹️ Stop Generation
          </button>
        </div>
      </section>
    </main>

    <!-- Success notification -->
    <transition name="fade">
      <div v-if="successMsg" class="notification success">
        {{ successMsg }}
      </div>
    </transition>
  </div>
</template>

<script setup>
import { ref, watch, computed } from 'vue';
import { startPPTGeneration, pollTaskStatus, cancelPPTGeneration } from './api/pptxService';
import confetti from 'canvas-confetti';

const htmlContent = ref('');
const selectedFile = ref(null);
const inputMode = ref('file'); // 'file' or 'text'
const isLoading = ref(false);
const isDragging = ref(false);
const successMsg = ref('');
const currentProgress = ref('');
const currentTaskId = ref(null);
const fileInput = ref(null);

const triggerFileInput = () => fileInput.value.click();

const handleFileSelect = (e) => {
  const file = e.target.files[0];
  if (file) selectedFile.value = file;
};

const handleFileDrop = (e) => {
  isDragging.value = false;
  const file = e.dataTransfer.files[0];
  if (file) selectedFile.value = file;
};

const clearFile = () => {
  selectedFile.value = null;
};

const handleSubmit = async () => {
  isLoading.value = true;
  successMsg.value = '';
  currentProgress.value = 'Connecting to AI...';
  
  try {
    // 1. Start Task
    const taskId = await startPPTGeneration(htmlContent.value, selectedFile.value, 50);
    currentTaskId.value = taskId;

    // 2. Poll for Status
    const result = await pollTaskStatus(
      taskId, 
      (msg) => { currentProgress.value = msg; }
    );
    
    if (result.success) {
      successMsg.value = '🚀 Success! Your deck is downloading.';
      confetti({
        particleCount: 150,
        spread: 70,
        origin: { y: 0.6 },
        colors: ['#6366f1', '#ec4899', '#8b5cf6']
      });
      setTimeout(() => successMsg.value = '', 5000);
    } else {
      // If result is not success but no error thrown, check if it was cancelled
      if (isLoading.value) { // If it wasn't manually stopped by handleCancel
        alert(`Error: ${result.error || 'Something went wrong'}`);
      }
    }
  } catch (err) {
    if (isLoading.value) { // Only show error if we didn't cancel manually
      alert('Something went wrong. Check the console.');
      console.error(err);
    }
  } finally {
    isLoading.value = false;
    currentTaskId.value = null;
    currentProgress.value = '';
  }
};

const handleCancel = async () => {
  if (currentTaskId.value) {
    currentProgress.value = 'Stopping generation...';
    await cancelPPTGeneration(currentTaskId.value);
    isLoading.value = false;
    currentTaskId.value = null;
    currentProgress.value = '';
  }
};
</script>

<style scoped>
.ingestion-tabs {
  display: flex;
  justify-content: center;
  gap: 1rem;
  margin-bottom: 2rem;
}

.tab-btn {
  background: rgba(255, 255, 255, 0.05);
  border: 1px solid var(--glass-border);
  color: #fff;
  padding: 8px 20px;
  border-radius: 30px;
  cursor: pointer;
  transition: all 0.3s ease;
  font-size: 0.9rem;
}

.tab-btn.active {
  background: var(--accent-1);
  border-color: var(--accent-1);
  box-shadow: 0 0 15px rgba(99, 102, 241, 0.4);
}

.cinematic-dropzone {
  border: 2px dashed var(--glass-border);
  border-radius: 20px;
  padding: 3rem 2rem;
  text-align: center;
  cursor: pointer;
  transition: all 0.3s ease;
  background: rgba(255, 255, 255, 0.02);
}

.cinematic-dropzone:hover, .cinematic-dropzone.dragging {
  border-color: var(--accent-1);
  background: rgba(99, 102, 241, 0.05);
  transform: translateY(-2px);
}

.drop-icon {
  font-size: 3rem;
  margin-bottom: 1rem;
}

.drop-text {
  font-size: 1.1rem;
  margin-bottom: 0.5rem;
}

.drop-hint {
  opacity: 0.6;
}

.file-info {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 1rem;
}

.file-icon {
  font-size: 3rem;
}

.file-name {
  font-weight: 500;
  max-width: 250px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.btn-clear {
  background: none;
  border: 1px solid var(--glass-border);
  color: #fff;
  padding: 6px 16px;
  border-radius: 20px;
  font-size: 0.8rem;
  cursor: pointer;
}

.btn-clear:hover {
  background: rgba(255,255,255,0.1);
}

.btn-cancel {
  margin-top: 1rem;
  background: rgba(239, 68, 68, 0.1);
  border: 1px solid rgba(239, 68, 68, 0.3);
  color: #fca5a5;
  padding: 8px 16px;
  border-radius: 12px;
  cursor: pointer;
  font-size: 0.85rem;
  font-weight: 500;
  transition: all 0.3s ease;
  width: 100%;
}

.btn-cancel:hover {
  background: rgba(239, 68, 68, 0.2);
  border-color: #ef4444;
  color: #fff;
  transform: translateY(-1px);
}

.notification {
  position: fixed;
  bottom: 30px;
  right: 30px;
  padding: 1rem 2rem;
  border-radius: 12px;
  background: var(--glass-bg);
  backdrop-filter: blur(10px);
  border: 1px solid var(--glass-border);
  box-shadow: var(--shadow-premium);
  z-index: 1000;
}
.notification.success {
  border-left: 4px solid var(--success);
}

/* Progress Indicator Styles */
.progress-container {
  margin-top: 2rem;
  padding: 1.5rem;
  background: rgba(255, 255, 255, 0.03);
  border-radius: 16px;
  border: 1px solid var(--glass-border);
  animation: fadeIn 0.5s ease;
}

.progress-bar {
  width: 100%;
  height: 6px;
  background: rgba(255, 255, 255, 0.1);
  border-radius: 10px;
  overflow: hidden;
  margin-bottom: 1rem;
}

.progress-fill {
  height: 100%;
  width: 40%; /* Animated default */
  background: linear-gradient(90deg, var(--accent-1), var(--accent-2));
  border-radius: 10px;
  animation: pulse-progress 2s infinite ease-in-out;
}

.progress-status {
  font-size: 0.9rem;
  color: #fff;
  opacity: 0.9;
  font-weight: 500;
}

@keyframes pulse-progress {
  0% { transform: translateX(-100%); }
  50% { transform: translateX(50%); }
  100% { transform: translateX(100%); }
}

@keyframes fadeIn {
  from { opacity: 0; transform: translateY(10px); }
  to { opacity: 1; transform: translateY(0); }
}
</style>
