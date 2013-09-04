function jq( myid ) {
	return "#" + myid.replace( /(:|\.|\[|\])/g, "\\$1" );
}

function registerMarkAction(container, element, url) {
	container.on("click", element, {url: url}, updateChecked);
}

function updateChecked(event) {
	event.preventDefault();

	var id = $(this).prop("id");
	var parts = id.split("_");
	parts.shift();
	var fileName = parts.join("_");
	var marked = $(this).html() == "unmark";
	var ajaxArgs = {
		type: "POST",
		url: event.data.url,
		data: {
			file: fileName,
			marked: marked
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
	var photoContainer = "container_" + data.details.file;
	var markedBlock = "mark_" + data.details.file;
	var containerElement = $(jq("#" + photoContainer));
	var markElement = $(jq("#" + markedBlock));
	if (data.details.marked == true) {
		markElement.html("unmark");
		containerElement.addClass("marked");
	} else {
		markElement.html("mark");
		containerElement.removeClass("marked");
	}
}
