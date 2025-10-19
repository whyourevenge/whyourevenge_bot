// https://viscously-unmeliorated-bibi.ngrok-free.dev

document.addEventListener('DOMContentLoaded', function() {
    const tg = window.Telegram.WebApp;
    tg.expand();

    // Отримуємо всі елементи
    const loader = document.getElementById('loader');
    const profileCard = document.getElementById('profile-card');
    const createPrompt = document.getElementById('create-prompt');
    const creationFormDiv = document.getElementById('creation-form');
    const form = document.getElementById('form');
    const likeButton = document.getElementById('like-button');
    const likeCounter = document.getElementById('like-counter');

    // Нові елементи для прогрес-бару
    const loaderOverlay = document.getElementById('loader-overlay');
    const progressBarFill = document.getElementById('progress-bar-fill');
    const progressText = document.getElementById('progress-text');

    const GET_PROFILE_URL = 'https://viscously-unmeliorated-bibi.ngrok-free.dev/get_profile';
    const LIKE_PROFILE_URL = 'https://viscously-unmeliorated-bibi.ngrok-free.dev/like_profile';
    const CREATE_PROFILE_URL = 'https://viscously-unmeliorated-bibi.ngrok-free.dev/create_profile';

    let receiverId = null;

    // ... (функції showProfile та showCreationPrompt без змін) ...
    function showProfile(data) {
        receiverId = data.user_id;
        document.getElementById('user-photo').src = data.photo_url;
        document.getElementById('user-name').textContent = data.name;
        document.getElementById('user-age').textContent = `Возраст: ${data.age}`;
        document.getElementById('user-bio').textContent = data.bio;
        likeCounter.textContent = data.likes_count;
        if (data.has_liked || data.is_own_profile) {
            likeButton.classList.add('liked');
            likeButton.disabled = true;
        }
        loader.classList.add('hidden');
        profileCard.classList.remove('hidden');
    }
    function showCreationPrompt() {
        loader.classList.add('hidden');
        profileCard.classList.add('hidden');
        createPrompt.classList.remove('hidden');
    }

    // ... (код для завантаження профілю fetch без змін) ...
    fetch(GET_PROFILE_URL, { method: 'POST', headers: { 'Content-Type': 'text/plain' }, body: tg.initData })
        .then(response => {
            if (response.status === 404) {
                showCreationPrompt();
                throw new Error('Profile not found');
            }
            if (!response.ok) { throw new Error('Network error'); }
            return response.json();
        })
        .then(data => { if (data) showProfile(data); })
        .catch(error => console.error(error.message));

    // ... (код для лайків без змін) ...
    likeButton.addEventListener('click', () => {
        if (!receiverId) return;
        likeButton.disabled = true;
        fetch(LIKE_PROFILE_URL, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ initData: tg.initData, receiver_id: receiverId })})
            .then(res => res.json())
            .then(data => {
                if (data.success) {
                    likeCounter.textContent = parseInt(likeCounter.textContent) + 1;
                    likeButton.classList.add('liked');
                } else {
                    likeButton.disabled = false;
                    tg.showAlert(data.message || 'Не удалось поставить лайк.');
                }
            });
    });

    // ... (код для кнопки "Створити профіль" без змін) ...
    document.getElementById('create-button').addEventListener('click', () => {
        createPrompt.classList.add('hidden');
        creationFormDiv.classList.remove('hidden');
    });

    // 👈 ОСНОВНІ ЗМІНИ ТУТ: Логіка відправки форми з анімацією
    form.addEventListener('submit', function(event) {
        event.preventDefault();

        // Показуємо оверлей
        loaderOverlay.classList.remove('hidden');

        let progress = 0;
        // Симулюємо прогрес завантаження
        const interval = setInterval(() => {
            progress += Math.random() * 10;
            if (progress > 95) {
                progress = 95; // Зупиняємось на 95%, чекаючи відповіді сервера
                clearInterval(interval);
            }
            progressBarFill.style.width = progress + '%';
            progressText.textContent = Math.round(progress) + '%';
        }, 200);

        const formData = new FormData();
        formData.append('initData', tg.initData);
        formData.append('name', document.getElementById('name-input').value);
        formData.append('age', document.getElementById('age-input').value);
        formData.append('bio', document.getElementById('bio-input').value);
        formData.append('photo', document.getElementById('photo-input').files[0]);

        fetch(CREATE_PROFILE_URL, {
            method: 'POST',
            body: formData
        })
        .then(response => response.json())
        .then(data => {
            clearInterval(interval); // Зупиняємо симуляцію
            // Робимо фінальний ривок до 100%
            progressBarFill.style.width = '100%';
            progressText.textContent = '100%';

            setTimeout(() => { // Чекаємо трохи, щоб користувач побачив 100%
                loaderOverlay.classList.add('hidden');
                if (data.success) {
                    tg.showAlert('Твій профіль успішно створено!', () => {
                        window.location.reload();
                    });
                } else {
                    tg.showAlert(data.message || 'Сталася помилка при створенні профілю.');
                }
                // Скидаємо прогрес-бар для наступного разу
                setTimeout(() => {
                    progressBarFill.style.width = '0%';
                    progressText.textContent = '0%';
                }, 500);
            }, 500);
        })
        .catch(error => {
            clearInterval(interval);
            loaderOverlay.classList.add('hidden');
            console.error('Error creating profile:', error);
            tg.showAlert('Сталася помилка мережі.');
        });
    });
});