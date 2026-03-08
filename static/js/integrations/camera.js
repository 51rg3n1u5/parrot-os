/**
 * ParrotOS - Camera Integration
 * Kamera-integration för rörelse/skrik-detektering
 */

ParrotOS.camera = {
    streamUrl: null,
    detecting: false,
    
    /**
     * Starta camera stream
     */
    async startStream(elementId) {
        try {
            const video = document.getElementById(elementId);
            if (!video) throw new Error('Video element not found');
            
            const stream = await navigator.mediaDevices.getUserMedia({ 
                video: { facingMode: 'user' } 
            });
            
            video.srcObject = stream;
            this.streamUrl = stream;
            
            return { success: true };
        } catch (e) {
            console.error('Camera error:', e);
            return { success: false, error: e.message };
        }
    },
    
    /**
     * Stoppa stream
     */
    stopStream() {
        if (this.streamUrl) {
            this.streamUrl.getTracks().forEach(track => track.stop());
            this.streamUrl = null;
        }
    },
    
    /**
     * Kolla status (rörelse, ljud)
     */
    async getStatus() {
        try {
            const res = await fetch('/api/camera/status');
            return await res.json();
        } catch (e) {
            return { error: e.message };
        }
    },
    
    /**
     * Aktivera detektering
     */
    async startDetection(callback) {
        this.detecting = true;
        
        // Polling för status (kan ersättas med WebSocket)
        const poll = async () => {
            if (!this.detecting) return;
            
            const status = await this.getStatus();
            if (status.motion_detected || status.sound_detected) {
                callback(status);
            }
            
            setTimeout(poll, 1000);
        };
        
        poll();
    },
    
    /**
     * Stoppa detektering
     */
    stopDetection() {
        this.detecting = false;
    }
};