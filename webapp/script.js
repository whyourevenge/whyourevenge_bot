// https://viscously-unmeliorated-bibi.ngrok-free.dev

document.addEventListener('DOMContentLoaded', function() {
    const tg = window.Telegram.WebApp;
    tg.expand();

    // Элементы интерфейса
    const loader = document.getElementById('loader');
    const profileCard = document.getElementById('profile-card');
    const createPrompt = document.getElementById('create-prompt');
    const creationFormDiv = document.getElementById('creation-form');
    const form = document.getElementById('form');
    const likeButton = document.getElementById('like-button');
    const likeCounter = document.getElementById('like-counter');
    
    // Адреса
    const GET_PROFILE_URL = 'https://viscously-unmeliorated-bibi.ngrok-free.dev/get_profile';    // 👈 ЗАМЕНИ НА СВОЙ NGROK АДРЕС
    const LIKE_PROFILE_URL = 'https://viscously-unmeliorated-bibi.ngrok-free.dev/like_profile';   // 👈 И СЮДА ТОЖЕ
    const CREATE_PROFILE_URL = 'https://viscously-unmeliorated-bibi.ngrok-free.dev/create_profile';

    let receiverId = null; // ID пользователя, чью анкету мы смотрим

    // Функция показа профиля
    function showProfile(data) {
        receiverId = data.user_id; // Сохраняем ID пользователя
        
        document.getElementById('user-photo').src = data.photo_url;
        document.getElementById('user-name').textContent = data.name;
        document.getElementById('user-age').textContent = `Возраст: ${data.age}`;
        document.getElementById('user-bio').textContent = data.bio;
        
        // Обновляем секцию лайков
        likeCounter.textContent = data.likes_count;
        if (data.has_liked) {
            likeButton.classList.add('liked');
            likeButton.disabled = true; // Уже лайкнули, блокируем кнопку
        }
        
        // Если пользователь смотрит свой собственный профиль, блокируем кнопку лайка
        if (data.is_own_profile) {
            likeButton.disabled = true;
        }

        loader.classList.add('hidden');
        profileCard.classList.remove('hidden');
    }

    // Загрузка профиля
    fetch(GET_PROFILE_URL, {
        method: 'POST',
        headers: { 'Content-Type': 'text/plain' },
        body: tg.initData
    })
    .then(response => {
        if (response.status === 404) {
            loader.classList.add('hidden');
            createPrompt.classList.remove('hidden');
            throw new Error('Profile not found');
        }
        return response.json();
    })
    .then(data => {
        if (data) showProfile(data);
    })
    .catch(error => console.error(error.message));

    // Обработчик нажатия на кнопку лайка
    likeButton.addEventListener('click', () => {
        if (!receiverId) return;

        likeButton.disabled = true; // Блокируем, чтобы избежать двойных нажатий

        fetch(LIKE_PROFILE_URL, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ initData: tg.initData, receiver_id: receiverId })
        })
        .then(response => response.json())
        .then(data => {
            if (data.success) {
                // Если всё хорошо, обновляем интерфейс
                likeCounter.textContent = parseInt(likeCounter.textContent) + 1;
                likeButton.classList.add('liked');
            } else {
                // Если что-то пошло не так, разблокируем кнопку
                likeButton.disabled = false;
                tg.showAlert(data.message || 'Не удалось поставить лайк.');
            }
        });
    });

    // ... (код для создания профиля остаётся без изменений)
    document.getElementById('create-button').addEventListener('click', () => {
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
        fetch(CREATE_PROFILE_URL, { method: 'POST', body: formData })
        .then(res => res.json())
        .then(data => {
            tg.MainButton.hideProgress();
            if (data.success) {
                tg.showAlert('Твой профиль успешно создан!', () => { window.location.reload(); });
            } else {
                tg.showAlert(data.message || 'Ошибка при создании профиля.');
            }
        });
    });
});