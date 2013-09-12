function jq( myid ) {
	return "#" + myid.replace( /(:|\.|\[|\]|\/)/g, "\\$1" );
}

function registerMarkAction(container, element, url) {
	container.on("click", element, {url: url}, updateMarked);
}

function updateMarked(event) {
	event.preventDefault();

	var id = $(this).prop("id");
	var mark = $(this).html() == "mark";
	var action = mark ? "unmark" : "mark";
	var ajaxArgs = {
		type: "POST",
		url: event.data.url + action + "/" + id,
		data: {
			file: fileName,
			marked: mark
		},
		success: onSuccess,
		dataType: "json"
	}
	$.ajax(ajaxArgs);
}

function onSuccess(data) {
	if (!data.success) {
		return;
	}
	var photoContainer = "container_" + data.details.id;
	var markedBlock = "mark_" + data.details.id;
	var containerElement = $(jq(photoContainer));
	var markElement = $(jq(markedBlock));
	if (data.details.marked == true) {
		markElement.html("unmark");
		containerElement.addClass("marked");
	} else {
		markElement.html("mark");
		containerElement.removeClass("marked");
	}
}
