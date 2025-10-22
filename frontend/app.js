// State management
let selectedFiles = [];
let apiKey = '';

// DOM Elements
const apiKeyInput = document.getElementById('apiKey');
const fileInput = document.getElementById('fileInput');
const uploadButton = document.getElementById('uploadButton');
const demoShoeButton = document.getElementById('demoShoeButton');
const demoMugButton = document.getElementById('demoMugButton');
const fileCount = document.getElementById('fileCount');
const previewSection = document.getElementById('previewSection');
const imageGrid = document.getElementById('imageGrid');
const processButton = document.getElementById('processButton');
const statusMessage = document.getElementById('statusMessage');

// Initialize Three.js Scene
let scene, camera, renderer, cube, controls;

function initThreeJS() {
    const container = document.getElementById('threejs-container');
    
    // Scene
    scene = new THREE.Scene();
    scene.background = new THREE.Color(0x1a1a2e);
    
    // Camera
    camera = new THREE.PerspectiveCamera(75, 1, 0.1, 1000);
    camera.position.z = 5;
    
    // Renderer
    renderer = new THREE.WebGLRenderer({ antialias: true });
    renderer.setSize(400, 400);
    container.appendChild(renderer.domElement);
    
    // Cube
    const geometry = new THREE.BoxGeometry(2, 2, 2);
    const material = new THREE.MeshPhongMaterial({ 
        color: 0x6366f1,
        shininess: 100
    });
    cube = new THREE.Mesh(geometry, material);
    scene.add(cube);
    
    // Lighting
    const ambientLight = new THREE.AmbientLight(0xffffff, 0.5);
    scene.add(ambientLight);
    
    const pointLight = new THREE.PointLight(0xffffff, 1);
    pointLight.position.set(5, 5, 5);
    scene.add(pointLight);
    
    // Controls
    controls = new THREE.OrbitControls(camera, renderer.domElement);
    controls.enableDamping = true;
    controls.dampingFactor = 0.05;
    controls.enableZoom = true;
    controls.autoRotate = true;
    controls.autoRotateSpeed = 2;
    
    // Animation loop
    animate();
}

function animate() {
    requestAnimationFrame(animate);
    controls.update();
    renderer.render(scene, camera);
}

// Event Listeners
apiKeyInput.addEventListener('input', (e) => {
    apiKey = e.target.value;
    localStorage.setItem('photoroom_api_key', apiKey);
});

uploadButton.addEventListener('click', () => {
    fileInput.click();
});

demoShoeButton.addEventListener('click', () => {
    showStatus('Demo: Shoe dataset would be loaded here. Coming soon!', 'info');
    // In the future, this could load pre-captured shoe images
    // For now, just show an informative message
});

demoMugButton.addEventListener('click', () => {
    showStatus('Demo: Mug dataset would be loaded here. Coming soon!', 'info');
    // In the future, this could load pre-captured mug images
    // For now, just show an informative message
});

fileInput.addEventListener('change', (e) => {
    const files = Array.from(e.target.files);
    
    if (files.length === 0) return;
    
    selectedFiles = files;
    updateFileCount();
    displayImagePreviews();
    previewSection.style.display = 'block';
});

processButton.addEventListener('click', async () => {
    if (selectedFiles.length === 0) {
        showStatus('Please select images first', 'error');
        return;
    }
    
    if (!apiKey) {
        showStatus('Please enter your Photoroom API key', 'error');
        return;
    }
    
    await processImages();
});

// Functions
function updateFileCount() {
    const count = selectedFiles.length;
    fileCount.textContent = count === 1 
        ? '1 image selected' 
        : `${count} images selected`;
}

function displayImagePreviews() {
    imageGrid.innerHTML = '';
    
    selectedFiles.forEach((file, index) => {
        const reader = new FileReader();
        
        reader.onload = (e) => {
            const imageItem = document.createElement('div');
            imageItem.className = 'image-item';
            
            const img = document.createElement('img');
            img.src = e.target.result;
            img.alt = file.name;
            
            const removeBtn = document.createElement('button');
            removeBtn.className = 'remove-btn';
            removeBtn.innerHTML = '×';
            removeBtn.onclick = () => removeImage(index);
            
            imageItem.appendChild(img);
            imageItem.appendChild(removeBtn);
            imageGrid.appendChild(imageItem);
        };
        
        reader.readAsDataURL(file);
    });
}

function removeImage(index) {
    selectedFiles.splice(index, 1);
    updateFileCount();
    
    if (selectedFiles.length === 0) {
        previewSection.style.display = 'none';
        fileInput.value = '';
    } else {
        displayImagePreviews();
    }
}

async function processImages() {
    processButton.disabled = true;
    showStatus('Processing images...', 'info');
    
    try {
        const formData = new FormData();
        
        // Add all files
        selectedFiles.forEach(file => {
            formData.append('files', file);
        });
        
        // Add API key
        formData.append('photoroom_api_key', apiKey);
        
        // Replace with your actual backend endpoint
        const response = await fetch('http://localhost:8000/', {
            method: 'POST',
            body: formData
        });
        
        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }
        
        const result = await response.json();
        
        showStatus(`Success! Processed ${result.files_received} images`, 'success');
        console.log('Processing result:', result);
        
        // Here you could update the 3D viewer with the processed result
        // For now, we just show the success message
        
    } catch (error) {
        console.error('Error processing images:', error);
        showStatus(`Error: ${error.message}`, 'error');
    } finally {
        processButton.disabled = false;
    }
}

function showStatus(message, type) {
    statusMessage.textContent = message;
    statusMessage.className = `status-message ${type}`;
    
    // Auto-hide after 5 seconds for success messages
    if (type === 'success') {
        setTimeout(() => {
            statusMessage.className = 'status-message';
        }, 5000);
    }
}

// Load saved API key
const savedApiKey = localStorage.getItem('photoroom_api_key');
if (savedApiKey) {
    apiKey = savedApiKey;
    apiKeyInput.value = savedApiKey;
}

// Initialize Three.js when page loads
window.addEventListener('load', () => {
    initThreeJS();
});

// Handle window resize for Three.js
window.addEventListener('resize', () => {
    const container = document.getElementById('threejs-container');
    const width = Math.min(400, container.clientWidth);
    const height = 400;
    
    camera.aspect = width / height;
    camera.updateProjectionMatrix();
    renderer.setSize(width, height);
});

