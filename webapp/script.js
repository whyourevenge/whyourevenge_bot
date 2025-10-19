// https://viscously-unmeliorated-bibi.ngrok-free.dev

document.addEventListener('DOMContentLoaded', function() {
    const tg = window.Telegram.WebApp;
    tg.expand();

    const loader = document.getElementById('loader');
    const profileCard = document.getElementById('profile-card');
    const createPrompt = document.getElementById('create-prompt');
    const creationFormDiv = document.getElementById('creation-form');
    const form = document.getElementById('form');
    const likeButton = document.getElementById('like-button');
    const likeCounter = document.getElementById('like-counter');
    
    const GET_PROFILE_URL = 'https://viscously-unmeliorated-bibi.ngrok-free.dev/get_profile';    // 👈 ЗАМЕНИ НА СВОЙ NGROK АДРЕС
    const LIKE_PROFILE_URL = 'https://viscously-unmeliorated-bibi.ngrok-free.dev/like_profile';   // 👈 И СЮДА ТОЖЕ
    const CREATE_PROFILE_URL = 'https://viscously-unmeliorated-bibi.ngrok-free.dev/create_profile';

    let receiverId = null; 

    // 👈 НОВОЕ: Читаем user_id из URL-параметра
    const urlParams = new URLSearchParams(window.location.search);
    const profileUserId = urlParams.get('user_id');

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

    // 👈 ОБНОВЛЕНО: Отправляем на бекенд и ID пользователя для просмотра
    const requestBody = {
        initData: tg.initData
    };
    if (profileUserId) {
        requestBody.profile_user_id = profileUserId;
    }

    fetch(GET_PROFILE_URL, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(requestBody)
    })
    .then(response => {
        if (response.status === 404) {
            showCreationPrompt();
            throw new Error('Profile not found');
        }
        return response.json();
    })
    .then(data => {
        if (data && !data.error) showProfile(data);
    })
    .catch(error => console.error(error.message));

    likeButton.addEventListener('click', () => {
        if (!receiverId) return;
        likeButton.disabled = true;
        fetch(LIKE_PROFILE_URL, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ initData: tg.initData, receiver_id: receiverId })
        })
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