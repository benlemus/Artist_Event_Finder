document.addEventListener("DOMContentLoaded", async () => {
  const topArtistList = document.getElementById("top-artist-list");
  const featuredEventsContainer = document.getElementById("featured-events");
  topArtistList.innerHTML = "<h3> Loading Events... </h3>";

  try {
    const res = await axios.get("/top-artists-events");
    const data = res.data;

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

      if (index == 0) {
        eventGroup.slice(0, 4).forEach((event, index) => {
          const newFeatured = document.createElement("div");
          newFeatured.className = "col";
          if (index == 2 || index == 3) {
            newFeatured.style.marginTop = "2vh";
          }

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
          fImg.className = "img-fluid rounded-start";
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
          fWishBtn.className = "btn btn-success ms-3";
          fWishBtn.textContent = "Add to Wishlist";
          fWishBtn.href = "/add-to-wishlist";

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
        cardWishBtn.className = "btn btn-success ms-3";
        cardWishBtn.textContent = "Add to Wishlist";
        cardWishBtn.href = "/add-to-wishlist";

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
});
