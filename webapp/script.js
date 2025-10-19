// https://viscously-unmeliorated-bibi.ngrok-free.dev

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

    // 1. Намагаємось отримати анкету
    fetch(GET_PROFILE_URL, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ initData: tg.initData })
    })
    .then(response => {
        // 👈 ОСЬ ВИПРАВЛЕННЯ: Спочатку перевіряємо статус
        if (response.status === 404) {
            // Якщо анкети немає, показуємо кнопку створення
            showCreationPrompt();
            // І зупиняємо подальшу обробку, кинувши контрольовану помилку
            throw new Error('Profile not found, showing creation form.');
        }
        if (!response.ok) {
            // Для всіх інших помилок
            throw new Error('Network response was not ok.');
        }
        // Тільки якщо все добре (статус 200), перетворюємо відповідь у JSON
        return response.json();
    })
    .then(data => {
        // Цей блок тепер виконається тільки для успішної відповіді
        showProfile(data);
    })
    .catch(error => {
        // Ловимо помилки. Якщо це наша "контрольована" помилка - нічого не робимо.
        if (error.message === 'Profile not found, showing creation form.') {
            console.log('Profile not found, form is displayed.');
        } else {
            // Для реальних помилок мережі показуємо повідомлення
            console.error('Error fetching profile:', error);
            loader.textContent = 'Сталася помилка мережі. Спробуйте пізніше.';
        }
    });

    // 2. Слухаємо клік на кнопку "Створити профіль" (код без змін)
    createButton.addEventListener('click', () => {
        createPrompt.classList.add('hidden');
        creationFormDiv.classList.remove('hidden');
    });

    // 3. Слухаємо відправку форми (код без змін)
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
                tg.showAlert('Твій профіль успішно створено!', () => {
                    window.location.reload();
                });
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