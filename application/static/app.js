document.addEventListener("DOMContentLoaded", async () => {
  let is_logged_in = false;
  let spotify_connected = false;

  try {
    const res = await axios.get("/get-authorization");
    const data = await res.data;

    is_logged_in = data.login;
    spotify_connected = data.spotify;
  } catch (error) {
    console.log("could not get log in/spotify info");
  }

  const topArtistList = document.getElementById("top-artist-list");
  const featuredEventsContainer = document.getElementById("featured-events");
  const showFeaturedEvents = document.getElementById("show-featured-events");
  const showTopTracksBehind = document.getElementById("show-top-tracks-behind");
  const showTopTracks = document.getElementById("show-top-tracks");

  if (spotify_connected == false) {
    showFeaturedEvents.style.display = "none";
    showTopTracksBehind.style.display = "none";
    showTopTracks.style.display = "none";
    return;
  } else if (spotify_connected == true) {
    showFeaturedEvents.style.display = "block";
    showTopTracksBehind.style.display = "block";
    showTopTracks.style.display = "block";
  }
  try {
    const res = await axios.get("/top-artists-events");
    const data = await res.data;
    const wishlist = await axios.get("/get-wishlist");

    topArtistList.innerHTML = "";

    data.forEach((eventGroup, index) => {
      const featuredEvents = document.createElement("div");
      featuredEvents.className = "row row-cols-2 mx-auto";
      featuredEvents.style.maxWidth = "60vw";

      const carouselItem = document.createElement("div");
      if (index == 0) {
        carouselItem.className = "carousel-item active";
      } else {
        carouselItem.className = "carousel-item";
      }
      const cardGroup = document.createElement("div");
      cardGroup.className = "card-group";

      if (index == 0 || index == 1) {
        eventGroup.forEach((event, index) => {
          const newFeatured = document.createElement("div");
          newFeatured.className = "col";

          const featureCard = document.createElement("div");
          featureCard.className = "card mb-3";
          featureCard.style.maxWidth = "800px";
          featureCard.style.minHeight = "350px";

          const fRow = document.createElement("div");
          fRow.className = "row g-0";
          fRow.style.minHeight = "350px";

          const fImgCol = document.createElement("div");
          fImgCol.className = "col-md-4";

          const fImg = document.createElement("img");
          fImg.className = "img-fluid rounded-start grid-card-img";
          fImg.src = event.image;

          const fBodyCol = document.createElement("div");
          fBodyCol.className = "col-md-8";

          const fBody = document.createElement("div");
          fBody.className = "card-body";

          const fTitle = document.createElement("h3");
          fTitle.className = "card-title";
          fTitle.textContent = event.name;

          const fCity = document.createElement("p");
          fCity.className = "card-text";
          fCity.textContent = event.location;

          const fDate = document.createElement("p");
          fDate.className = "card-text";
          fDate.textContent = event.date;

          const fArtist = document.createElement("h5");
          fArtist.className = "card-title";
          fArtist.textContent = event.artist;

          const fTicketBtn = document.createElement("a");
          fTicketBtn.className = "btn btn-primary";
          fTicketBtn.textContent = "Get Tickets";
          fTicketBtn.href = event.url;

          const fWishBtn = document.createElement("a");
          if (wishlist.data.includes(event.event_id)) {
            fWishBtn.className = "btn btn-danger ms-3 wishlistBtn";
            fWishBtn.textContent = "Remove from Wishlist";
            fWishBtn.dataset.eventid = event.event_id;
            // fWishBtn.href = `/remove-wishlist/${event.event_id}`;
          } else {
            fWishBtn.className = "btn btn-success ms-3 wishlistBtn";
            fWishBtn.textContent = "Add to Wishlist";
            fWishBtn.dataset.eventid = event.event_id;
            // fWishBtn.href = `/add-to-wishlist/${event.event_id}`;
          }

          fBody.append(fTitle, fCity, fDate, fArtist, fTicketBtn, fWishBtn);
          fBody.style.fontSize = "20px";
          fBodyCol.append(fBody);
          fImgCol.append(fImg);

          fRow.append(fImgCol, fBodyCol);
          featureCard.append(fRow);
          newFeatured.append(featureCard);
          featuredEvents.append(newFeatured);
          featuredEventsContainer.append(featuredEvents);
        });
      }

      eventGroup.forEach((event) => {
        const card = document.createElement("div");
        card.className = "card";

        const cardImg = document.createElement("img");
        cardImg.src = event.image;
        cardImg.className = "card-img-top";
        cardImg.style = "max-height: 230px";

        const cardBody = document.createElement("div");
        cardBody.className = "card-body";

        const cardTitle = document.createElement("h5");
        cardTitle.className = "card-title";
        cardTitle.textContent = event.name;

        const cardCity = document.createElement("p");
        cardCity.className = "card-text";
        cardCity.textContent = event.location;

        const cardDate = document.createElement("p");
        cardDate.className = "card-text";
        cardDate.textContent = event.date;

        const cardArtist = document.createElement("h5");
        cardArtist.className = "card-title";
        cardArtist.textContent = event.artist;

        const cardTicketBtn = document.createElement("a");
        cardTicketBtn.className = "btn btn-primary";
        cardTicketBtn.textContent = "Get Tickets";
        cardTicketBtn.href = event.url;

        const cardWishBtn = document.createElement("a");
        if (wishlist.data.includes(event.event_id)) {
          cardWishBtn.className = "btn btn-danger ms-3 wishlistBtn";
          cardWishBtn.textContent = "Remove from Wishlist";
          cardWishBtn.dataset.eventid = event.event_id;
          // cardWishBtn.href = `/remove-wishlist/${event.event_id}`;
        } else {
          cardWishBtn.className = "btn btn-success ms-3 wishlistBtn";
          cardWishBtn.textContent = "Add to Wishlist";
          cardWishBtn.dataset.eventid = event.event_id;
          // cardWishBtn.href = `/add-to-wishlist/${event.event_id}`;
        }

        cardBody.append(
          cardTitle,
          cardCity,
          cardDate,
          cardArtist,
          cardTicketBtn,
          cardWishBtn
        );

        card.append(cardImg, cardBody);
        cardGroup.append(card);
      });
      carouselItem.append(cardGroup);
      topArtistList.append(carouselItem);
    });
  } catch (error) {
    console.log("Error getting top artist events:", error);
    topArtistList.innerHTML = "<h3> Could Not Get Events... </h3>";
  }
  document.addEventListener("click", async (event) => {
    if (event.target.classList.contains("wishlistBtn")) {
      const button = event.target;
      const eventId = button.dataset.eventid;
      try {
        if (button.textContent == "Add to Wishlist") {
          const res = await axios.post(`/add-to-wishlist/${eventId}`);
        } else if (button.textContent == "Remove from Wishlist") {
          const res = await axios.post(`/remove-wishlist/${eventId}`);
        }

        button.classList.toggle("btn-success");
        button.classList.toggle("btn-danger");
        button.textContent =
          button.textContent === "Add to Wishlist"
            ? "Remove from Wishlist"
            : "Add to Wishlist";
      } catch (error) {
        console.log(error);
      }
    }
  });
});
