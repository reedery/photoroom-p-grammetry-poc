# Photogrammetry POC - Frontend

## How to Run

**Python 3.x:**

```bash
cd frontend
python3 -m http.server 8080
```

Then open your browser and navigate to:

```
http://localhost:8080
```

## Usage

1. **Enter API Key**: Enter your Photoroom API key in the input field (it will be saved in your browser's local storage)

2. **Read the Tips**: Review the photogrammetry tips section to understand how to take good photos for 3D reconstruction

3. **Select Images**:

   - Click "Select Images" to choose multiple images from your device
   - Or click "👟 Try a Shoe" or "☕ Try a Mug" for demo datasets (coming soon)

4. **Preview**: Review the selected images in the preview grid. You can remove individual images by hovering over them and clicking the × button

5. **Process**: Click "Process Images" to send the images to the backend for processing

6. **3D Viewer**: The Three.js viewer shows a rotating cube (this will be replaced with your 3D model once processing is complete)

### Important: Taking Good Photos

The app includes detailed tips, but remember:

- ✅ **DO**: Walk around the object with your camera
- ❌ **DON'T**: Rotate the object on a turntable
- COLMAP needs camera movement with parallax, not object rotation

## Backend Connection

The frontend is configured to send requests to:

```
http://localhost:8000/
```

Make sure your Modal backend is running and accessible at this URL. You can modify the endpoint in `app.js` if needed:

```javascript
const response = await fetch("http://localhost:8000/", {
  method: "POST",
  body: formData,
});
```

## File Structure

```
frontend/
├── index.html      # Main HTML structure
├── style.css       # Styling (Photoroom-inspired design)
├── app.js          # JavaScript logic & Three.js integration
└── README.md       # This file
```

## Technologies Used

- **HTML5**: Semantic markup
- **CSS3**: Modern styling with gradients, flexbox, and grid
- **JavaScript (ES6+)**: Async/await, File API
- **Three.js**: 3D visualization with OrbitControls
- **LocalStorage**: Persistent API key storage

## Customization

### Change Backend URL

Edit `app.js` line ~140:

```javascript
const response = await fetch('YOUR_BACKEND_URL', {
```

### Modify Three.js Scene

Edit the `initThreeJS()` function in `app.js` to customize:

- Cube size and color
- Camera position
- Lighting
- Auto-rotation speed

### Adjust Colors

Edit CSS variables in `style.css`:

```css
:root {
  --primary-color: #6366f1;
  --primary-hover: #4f46e5;
  /* ... more variables */
}
```

## Browser Support

- Chrome/Edge (latest)
- Firefox (latest)
- Safari (latest)
- Mobile browsers (iOS Safari, Chrome Mobile)

## Notes

- The API key is stored in your browser's localStorage for convenience
- Images are not uploaded until you click "Process Images"
- The Three.js viewer currently shows a demo cube - this will be replaced with your 3D reconstruction
- Make sure to enable CORS on your backend if running on different ports
