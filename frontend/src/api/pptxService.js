import axios from 'axios';

// Detect if we are in production and set a smart default for the API URL
// In development: http://localhost:8001
// In production: /api (proxied via Nginx)
const API_BASE_URL = import.meta.env.VITE_API_URL ||
    (import.meta.env.PROD ? '/api' : 'http://localhost:8001');

/**
 * Trigger the background task and return the task_id
 */
export const startPPTGeneration = async (htmlContent, file, maxSlides = 50) => {
    try {
        const formData = new FormData();
        if (htmlContent) formData.append('html_content', htmlContent);
        if (file) formData.append('file', file);
        formData.append('max_slides', maxSlides);

        console.log(`Starting generation at: ${API_BASE_URL}/generate-pptx`);

        const startResponse = await axios.post(`${API_BASE_URL}/generate-pptx`, formData, {
            headers: { 'Content-Type': 'multipart/form-data' },
        });

        return startResponse.data.task_id;
    } catch (error) {
        console.error('Error starting generation:', error);
        throw error;
    }
};

/**
 * Poll the backend for task status with built-in retry logic
 */
export const pollTaskStatus = async (taskId, onProgress, interval = 2000, retryCount = 0) => {
    const MAX_RETRIES = 5;

    try {
        const response = await axios.get(`${API_BASE_URL}/task-status/${taskId}`);

        const { status, result } = response.data;
        console.log(`Task ${taskId} status: ${status}`, result);

        if (status === 'PROGRESS') {
            if (onProgress && result && result.message) {
                onProgress(result.message);
            }
            // Reset retry count on successful response
            await new Promise(resolve => setTimeout(resolve, interval));
            return pollTaskStatus(taskId, onProgress, interval, 0);
        } else if (status === 'SUCCESS') {
            // 3. Trigger Download via hidden anchor for better reliability
            const downloadUrl = `${API_BASE_URL}/download/${taskId}`;
            console.log('Download ready! Triggering:', downloadUrl);

            const link = document.createElement('a');
            link.href = downloadUrl;
            link.setAttribute('download', ''); // Handled by server headers
            document.body.appendChild(link);
            link.click();
            document.body.removeChild(link);

            return { success: true };
        } else if (status === 'FAILURE' || status === 'REVOKED') {
            const error = result && result.message ? result.message : 'Task failed or was cancelled';
            console.error('Task failed reported by backend:', error);
            return { success: false, error };
        } else {
            // PENDING or STARTED etc.
            if (onProgress) onProgress('Initialising task...');
            await new Promise(resolve => setTimeout(resolve, interval));
            return pollTaskStatus(taskId, onProgress, interval, 0);
        }
    } catch (error) {
        if (retryCount < MAX_RETRIES) {
            console.warn(`Polling connection error, retrying (${retryCount + 1}/${MAX_RETRIES})...`);
            await new Promise(resolve => setTimeout(resolve, interval * 1.5));
            return pollTaskStatus(taskId, onProgress, interval, retryCount + 1);
        }

        console.error('Max polling retries exceeded:', error);
        return { success: false, error: 'Connection lost while generating presentation. Please check your network.' };
    }
};

/**
 * Cancel a running PPT generation task
 */
export const cancelPPTGeneration = async (taskId) => {
    try {
        await axios.post(`${API_BASE_URL}/cancel-task/${taskId}`);
        return { success: true };
    } catch (error) {
        console.error('Error cancelling task:', error);
        return { success: false, error: error.message };
    }
};
