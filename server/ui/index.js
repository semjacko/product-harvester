function previewImage(event) {
    const file = event.target.files[0];
    const previewDiv = document.getElementById('preview');

    if (file) {
        const reader = new FileReader();
        reader.onload = function(e) {
            // Update the preview div with the uploaded image
            previewDiv.innerHTML = `<img src="${e.target.result}" alt="Image Preview">`;
        };
        reader.readAsDataURL(file); // Convert the image to a base64 URL
    } else {
        previewDiv.innerHTML = '<p>No image selected</p>';
    }
}

async function submitForm() {
    const model = document.getElementById('model').value;
    const apiKey = document.getElementById('api_key').value;
    const imageFile = document.getElementById('image_file').files[0];
    const responseDiv = document.getElementById('response');

    // Clear any previous responses
    responseDiv.innerHTML = '';

    if (!imageFile) {
        responseDiv.innerHTML = '<p style="color: red;">Please upload an image file.</p>';
        return;
    }

    // Convert image file to base64
    const base64Image = await toBase64(imageFile);

    try {
        // Make API request
        const response = await fetch('/api/process', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                model: model,
                api_key: apiKey,
                image_base64: base64Image
            })
        });

        // Parse and display response
        if (response.ok) {
            const result = await response.json();
            responseDiv.innerHTML = `<pre>${JSON.stringify(result, null, 2)}</pre>`;
        } else {
            const error = await response.json();
            responseDiv.innerHTML = `<p style="color: red;">Error: ${error.detail || 'Unable to process'}</p>`;
        }
    } catch (error) {
        responseDiv.innerHTML = `<p style="color: red;">Error: ${error.message}</p>`;
    }
}

// Helper function to convert image file to base64
function toBase64(file) {
    return new Promise((resolve, reject) => {
        const reader = new FileReader();
        reader.readAsDataURL(file);
        reader.onload = () => resolve(reader.result);
        reader.onerror = error => reject(error);
    });
}