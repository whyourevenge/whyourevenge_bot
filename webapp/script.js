// https://viscously-unmeliorated-bibi.ngrok-free.dev

// webapp/script.js

document.addEventListener('DOMContentLoaded', function() {
    const tg = window.Telegram.WebApp;
    tg.expand();

    const loader = document.getElementById('loader');
    const profileCard = document.getElementById('profile-card');
    const createPrompt = document.getElementById('create-prompt');
    const createButton = document.getElementById('create-button');
    const creationFormDiv = document.getElementById('creation-form');
    const form = document.getElementById('form');

    const GET_PROFILE_URL = 'https://viscously-unmeliorated-bibi.ngrok-free.dev/get_profile';    // 👈 НЕ ЗАБУДЬ ВСТАВИТИ СВОЮ NGROK АДРЕСУ
    const CREATE_PROFILE_URL = 'https://viscously-unmeliorated-bibi.ngrok-free.dev/create_profile'; // 👈 І СЮДИ ТЕЖ

    function showProfile(data) {
        document.getElementById('user-photo').src = data.photo_url;
        document.getElementById('user-name').textContent = data.name;
        document.getElementById('user-age').textContent = `Вік: ${data.age}`;
        document.getElementById('user-bio').textContent = data.bio;
        loader.classList.add('hidden');
        profileCard.classList.remove('hidden');
    }

    function showCreationPrompt() {
        loader.classList.add('hidden');
        profileCard.classList.add('hidden');
        createPrompt.classList.remove('hidden');
    }

    // 👈 ЗМІНЕНО: Відправляємо initData як чистий текст
    fetch(GET_PROFILE_URL, {
        method: 'POST',
        headers: { 'Content-Type': 'text/plain' }, // Змінили заголовок
        body: tg.initData // Відправляємо рядок напряму
    })
    .then(response => {
        if (response.status === 404) {
            showCreationPrompt();
            throw new Error('Profile not found, showing creation form.');
        }
        if (!response.ok) {
            throw new Error(`Network response was not ok, status: ${response.status}`);
        }
        return response.json();
    })
    .then(data => {
        showProfile(data);
    })
    .catch(error => {
        if (error.message.startsWith('Profile not found')) {
            console.log(error.message);
        } else {
            console.error('Error fetching profile:', error);
            loader.textContent = 'Сталася помилка мережі. Спробуйте пізніше.';
        }
    });

    createButton.addEventListener('click', () => {
        createPrompt.classList.add('hidden');
        creationFormDiv.classList.remove('hidden');
    });

    form.addEventListener('submit', function(event) {
        event.preventDefault();
        const formData = new FormData();
        formData.append('initData', tg.initData);
        formData.append('name', document.getElementById('name-input').value);
        formData.append('age', document.getElementById('age-input').value);
        formData.append('bio', document.getElementById('bio-input').value);
        formData.append('photo', document.getElementById('photo-input').files[0]);
        tg.MainButton.showProgress();
        fetch(CREATE_PROFILE_URL, {
            method: 'POST',
            body: formData
        })
        .then(response => response.json())
        .then(data => {
            tg.MainButton.hideProgress();
            if (data.success) {
                tg.showAlert('Твій профіль успішно створено!', () => { window.location.reload(); });
            } else {
                tg.showAlert(data.message || 'Сталася помилка при створенні профілю.');
            }
        })
        .catch(error => {
            tg.MainButton.hideProgress();
            console.error('Error creating profile:', error);
            tg.showAlert('Сталася помилка мережі.');
        });
    });
});