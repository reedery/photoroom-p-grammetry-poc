// State management
let selectedFile = null;
let apiKey = '';
let currentModel = null;

// DOM Elements
const apiKeyInput = document.getElementById('apiKey');
const fileInput = document.getElementById('fileInput');
const uploadButton = document.getElementById('uploadButton');
const demoShoeButton = document.getElementById('demoShoeButton');
const demoMugButton = document.getElementById('demoMugButton');
const fileCount = document.getElementById('fileCount');
const previewSection = document.getElementById('previewSection');
const imagePreview = document.getElementById('imagePreview');
const processButton = document.getElementById('processButton');
const processButtonText = document.getElementById('processButtonText');
const processingSpinner = document.getElementById('processingSpinner');
const statusMessage = document.getElementById('statusMessage');

// Initialize Three.js Scene
let scene, camera, renderer, controls;

function initThreeJS() {
    const container = document.getElementById('threejs-container');
    
    // Scene
    scene = new THREE.Scene();
    scene.background = new THREE.Color(0x1a1a2e);
    
    // Camera
    camera = new THREE.PerspectiveCamera(75, 1, 0.1, 1000);
    camera.position.set(0, 0, 5);
    
    // Renderer
    renderer = new THREE.WebGLRenderer({ antialias: true });
    renderer.setSize(400, 400);
    renderer.shadowMap.enabled = true;
    renderer.shadowMap.type = THREE.PCFSoftShadowMap;
    container.appendChild(renderer.domElement);
    
    // Enhanced lighting for better model visibility
    const ambientLight = new THREE.AmbientLight(0xffffff, 1.6);
    scene.add(ambientLight);
    
    // Main directional light
    const directionalLight1 = new THREE.DirectionalLight(0xffffff, 1.4);
    directionalLight1.position.set(5, 5, 5);
    directionalLight1.castShadow = true;
    scene.add(directionalLight1);
    
    // Secondary directional light for fill
    const directionalLight2 = new THREE.DirectionalLight(0xffffff, 0.8);
    directionalLight2.position.set(-5, -5, -5);
    scene.add(directionalLight2);
    
    // Additional rim light for better definition
    const directionalLight3 = new THREE.DirectionalLight(0xffffff, 0.8);
    directionalLight3.position.set(0, 5, -5);
    scene.add(directionalLight3);
    
    // Controls
    controls = new THREE.OrbitControls(camera, renderer.domElement);
    controls.enableDamping = true;
    controls.dampingFactor = 0.05;
    controls.enableZoom = true;
    controls.autoRotate = false;
    controls.autoRotateSpeed = 2;
    
    
    // Add a placeholder cube initially
    addPlaceholderCube();
    
    // Animation loop
    animate();
}


function addPlaceholderCube() {
    const geometry = new THREE.BoxGeometry(2, 2, 2);
    const material = new THREE.MeshPhongMaterial({ 
        color: 0x6366f1,
        shininess: 100
    });
    const cube = new THREE.Mesh(geometry, material);
    cube.castShadow = true;
    cube.receiveShadow = true;
    currentModel = cube;
    scene.add(cube);
}

function animate() {
    requestAnimationFrame(animate);
    controls.update();
    
    // Rotate the placeholder cube slowly
    if (currentModel && currentModel.geometry && currentModel.geometry.type === 'BoxGeometry') {
        currentModel.rotation.x += 0.005;
        currentModel.rotation.y += 0.005;
    }
    
    renderer.render(scene, camera);
}

// Load and display 3D model
function load3DModel(modelUrl, format = 'glb') {
    // Remove current model if exists
    if (currentModel) {
        scene.remove(currentModel);
        if (currentModel.geometry) currentModel.geometry.dispose();
        if (currentModel.material) {
            if (Array.isArray(currentModel.material)) {
                currentModel.material.forEach(mat => mat.dispose());
            } else {
                currentModel.material.dispose();
            }
        }
    }
    
    showStatus('Loading 3D model...', 'info');
    
    if (format === 'glb') {
        const loader = new THREE.GLTFLoader();
        loader.load(
            modelUrl,
            function (gltf) {
                const model = gltf.scene;
                
                // Center and scale the model
                const box = new THREE.Box3().setFromObject(model);
                const center = new THREE.Vector3();
                box.getCenter(center);
                model.position.sub(center);
                
                // Rotate model 90 degrees around X-axis to fix orientation
                model.rotation.x = -Math.PI / 2;
                
                const size = new THREE.Vector3();
                box.getSize(size);
                const maxDim = Math.max(size.x, size.y, size.z);
                const scale = 3 / maxDim;
                model.scale.set(scale, scale, scale);
                
                // Enable shadows for the model
                model.traverse(function (child) {
                    if (child.isMesh) {
                        child.castShadow = true;
                        child.receiveShadow = true;
                    }
                });
                
                currentModel = model;
                scene.add(model);
                
                controls.autoRotate = true;
                showStatus('3D model loaded successfully!', 'success');
            },
            function (xhr) {
                console.log((xhr.loaded / xhr.total * 100) + '% loaded');
            },
            function (error) {
                console.error('Error loading GLB:', error);
                showStatus('Error loading 3D model', 'error');
                addPlaceholderCube();
            }
        );
    } else if (format === 'ply') {
        const loader = new THREE.PLYLoader();
        loader.load(
            modelUrl,
            function (geometry) {
                geometry.computeVertexNormals();
                
                const material = new THREE.MeshPhongMaterial({ 
                    color: 0x6366f1,
                    shininess: 80,
                    vertexColors: geometry.attributes.color ? true : false
                });
                
                const mesh = new THREE.Mesh(geometry, material);
                
                // Center and scale the model
                geometry.computeBoundingBox();
                const center = new THREE.Vector3();
                geometry.boundingBox.getCenter(center);
                mesh.position.sub(center);
                
                const size = new THREE.Vector3();
                geometry.boundingBox.getSize(size);
                const maxDim = Math.max(size.x, size.y, size.z);
                const scale = 3 / maxDim;
                mesh.scale.set(scale, scale, scale);
                
                currentModel = mesh;
                scene.add(mesh);
                
                controls.autoRotate = true;
                showStatus('3D model loaded successfully!', 'success');
            },
            function (xhr) {
                console.log((xhr.loaded / xhr.total * 100) + '% loaded');
            },
            function (error) {
                console.error('Error loading PLY:', error);
                showStatus('Error loading 3D model', 'error');
                addPlaceholderCube();
            }
        );
    } else if (format === 'obj') {
        const loader = new THREE.OBJLoader();
        loader.load(
            modelUrl,
            function (object) {
                // Apply material to all meshes in the object
                object.traverse(function (child) {
                    if (child instanceof THREE.Mesh) {
                        child.material = new THREE.MeshPhongMaterial({ 
                            color: 0x6366f1,
                            shininess: 80
                        });
                    }
                });
                
                // Center and scale
                const box = new THREE.Box3().setFromObject(object);
                const center = new THREE.Vector3();
                box.getCenter(center);
                object.position.sub(center);
                
                const size = new THREE.Vector3();
                box.getSize(size);
                const maxDim = Math.max(size.x, size.y, size.z);
                const scale = 3 / maxDim;
                object.scale.set(scale, scale, scale);
                
                currentModel = object;
                scene.add(object);
                
                controls.autoRotate = true;
                showStatus('3D model loaded successfully!', 'success');
            },
            function (xhr) {
                console.log((xhr.loaded / xhr.total * 100) + '% loaded');
            },
            function (error) {
                console.error('Error loading OBJ:', error);
                showStatus('Error loading 3D model', 'error');
                addPlaceholderCube();
            }
        );
    }
}

// Event Listeners
apiKeyInput.addEventListener('input', (e) => {
    apiKey = e.target.value;
    localStorage.setItem('photoroom_api_key', apiKey);
});

uploadButton.addEventListener('click', () => {
    fileInput.click();
});

demoShoeButton.addEventListener('click', async () => {
    showStatus('Loading shoe image...', 'info');
    try {
        const response = await fetch('img/shoe.jpg');
        const blob = await response.blob();
        const file = new File([blob], 'shoe.jpg', { type: 'image/jpeg' });
        selectedFile = file;
        displayImagePreview();
        previewSection.style.display = 'block';
        fileCount.textContent = '1 image selected (Demo: Shoe)';
        showStatus('Shoe image loaded!', 'success');
    } catch (error) {
        console.error('Error loading shoe image:', error);
        showStatus('Error loading shoe image', 'error');
    }
});

demoMugButton.addEventListener('click', async () => {
    showStatus('Loading mug image...', 'info');
    try {
        const response = await fetch('img/mug.jpg');
        const blob = await response.blob();
        const file = new File([blob], 'mug.jpg', { type: 'image/jpeg' });
        selectedFile = file;
        displayImagePreview();
        previewSection.style.display = 'block';
        fileCount.textContent = '1 image selected (Demo: Mug)';
        showStatus('Mug image loaded!', 'success');
    } catch (error) {
        console.error('Error loading mug image:', error);
        showStatus('Error loading mug image', 'error');
    }
});

fileInput.addEventListener('change', (e) => {
    const file = e.target.files[0];
    
    if (!file) return;
    
    selectedFile = file;
    displayImagePreview();
    previewSection.style.display = 'block';
    fileCount.textContent = '1 image selected';
});

processButton.addEventListener('click', async () => {
    if (!selectedFile) {
        showStatus('Please select an image first', 'error');
        return;
    }
    
    if (!apiKey) {
        showStatus('Please enter your Photoroom API key', 'error');
        return;
    }
    
    await processImage();
});

// Functions
function displayImagePreview() {
    imagePreview.innerHTML = '';
    
    const reader = new FileReader();
    
    reader.onload = (e) => {
        const imageContainer = document.createElement('div');
        imageContainer.className = 'image-preview-container';
        
        const img = document.createElement('img');
        img.src = e.target.result;
        img.alt = selectedFile.name;
        img.className = 'preview-image';
        
        const removeBtn = document.createElement('button');
        removeBtn.className = 'remove-preview-btn';
        removeBtn.innerHTML = '× Remove';
        removeBtn.onclick = () => {
            selectedFile = null;
            previewSection.style.display = 'none';
            fileInput.value = '';
            fileCount.textContent = 'No image selected';
        };
        
        imageContainer.appendChild(img);
        imageContainer.appendChild(removeBtn);
        imagePreview.appendChild(imageContainer);
    };
    
    reader.readAsDataURL(selectedFile);
}

async function processImage() {
    // Show loading state
    processButton.disabled = true;
    processButtonText.textContent = 'Processing...';
    processingSpinner.style.display = 'inline-block';
    showStatus('Sending image to server for processing...', 'info');
    
    try {
        const formData = new FormData();
        formData.append('image', selectedFile);
        formData.append('photoroom_api_key', apiKey);
        
        // TODO: Update this endpoint when backend is ready
        const API_ENDPOINT = 'http://localhost:8000/process';
        
        const response = await fetch(API_ENDPOINT, {
            method: 'POST',
            body: formData
        });
        
        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }
        
        const result = await response.json();
        
        showStatus('Processing complete! Loading 3D model...', 'success');
        console.log('Processing result:', result);
        
        // Load the 3D model
        // Assuming the backend returns a URL or path to the 3D model file
        if (result.model_url) {
            // Determine format from URL or result (prioritize GLB)
            const format = result.format || 'glb';
            load3DModel(result.model_url, format);
        } else if (result.model_path) {
            // If backend returns a relative path
            load3DModel(result.model_path, result.format || 'glb');
        } else {
            throw new Error('No 3D model URL in response');
        }
        
    } catch (error) {
        console.error('Error processing image:', error);
        showStatus(`Error: ${error.message}`, 'error');
    } finally {
        // Reset button state
        processButton.disabled = false;
        processButtonText.textContent = 'Generate 3D Model';
        processingSpinner.style.display = 'none';
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
