import os
import shutil
import subprocess
from django.shortcuts import render, redirect, get_object_or_404
from django.http import FileResponse, HttpResponse
from django.conf import settings
from django.contrib.auth.decorators import login_required, user_passes_test

from .models import ClientFile, ClientProfile
from .forms import AddClientForm


# -------------------- Admin helpers -------------------- #
def is_admin(user):
    """Check if the user is a superuser (admin)."""
    return user.is_superuser


#@user_passes_test(is_admin)
from django.contrib.auth.models import User
from django.contrib import messages

def add_client(request):
    if request.method == "POST":
        form = AddClientForm(request.POST)
        if form.is_valid():
            username = form.cleaned_data['username']
            if User.objects.filter(username=username).exists():
                messages.error(request, "A user with that username already exists.")
                return render(request, "clients/add_client.html", {"form": form})

            storage_path = os.path.join(settings.USER_DATA_ROOT, username)
            form.instance.storage_path = storage_path
            client = form.save()
            os.makedirs(storage_path, exist_ok=True)
            return redirect('login')
    else:
        form = AddClientForm()
    return render(request, "clients/add_client.html", {"form": form})



@user_passes_test(is_admin)
def delete_client(request, user_id):
    """
    Delete a client, their storage folder, and associated DB entries.
    Admin only.
    """
    user = get_object_or_404(ClientProfile, id=user_id)
    storage_path = user.storage_path

    # Delete folder on disk if exists
    if os.path.exists(storage_path):
        shutil.rmtree(storage_path)

    # Delete user and profile
    user.user.delete()  # delete Django User
    user.delete()       # delete ClientProfile

    return redirect('admin_dashboard')  # or another page


# -------------------- Client Dashboard -------------------- #
@login_required
def dashboard(request):
    """
    Display client dashboard with all uploaded files and quota info.
    """
    client_profile = ClientProfile.objects.get(user=request.user)

    # Ensure storage folder exists
    if not os.path.exists(client_profile.storage_path):
        os.makedirs(client_profile.storage_path, exist_ok=True)

    # Sync disk files to DB if missing
    for f in os.listdir(client_profile.storage_path):
        if not client_profile.files.filter(name=f).exists():
            size_mb = os.path.getsize(os.path.join(client_profile.storage_path, f)) / (1024 * 1024)
            ClientFile.objects.create(client=client_profile, name=f, size=size_mb)

    files = client_profile.files.all()

    # Get quota info (optional, only if on Linux with quota configured)
    try:
        quota_info = subprocess.getoutput(f"quota -s {request.user.username}")
    except Exception:
        quota_info = "Quota info unavailable"

    return render(request, "clients/dashboard.html", {
        "files": files,
        "quota": quota_info
    })


# -------------------- File Operations -------------------- #
@login_required
def upload_file(request):
    """
    Handle client file uploads. Files are saved to disk and DB.
    """
    if request.method == "POST" and request.FILES.get("file"):
        client_profile = ClientProfile.objects.get(user=request.user)
        user_dir = client_profile.storage_path

        # Ensure storage folder exists
        os.makedirs(user_dir, exist_ok=True)

        uploaded_file = request.FILES["file"]
        file_path = os.path.join(user_dir, uploaded_file.name)

        # Save file to disk
        with open(file_path, 'wb+') as dest:
            for chunk in uploaded_file.chunks():
                dest.write(chunk)

        # Save metadata to DB
        size_mb = os.path.getsize(file_path) / (1024 * 1024)
        ClientFile.objects.create(client=client_profile, name=uploaded_file.name, size=size_mb)

    return redirect("dashboard")


@login_required
def download_file(request, filename):
    """
    Download a file from the client's storage folder.
    """
    client_profile = ClientProfile.objects.get(user=request.user)
    file_path = os.path.join(client_profile.storage_path, filename)
    if os.path.exists(file_path):
        return FileResponse(open(file_path, "rb"), as_attachment=True)
    return HttpResponse("File not found", status=404)


@login_required
def delete_file(request, filename):
    """
    Delete a file from the client's storage folder and DB.
    """
    client_profile = ClientProfile.objects.get(user=request.user)
    file_path = os.path.join(client_profile.storage_path, filename)

    if os.path.exists(file_path):
        os.remove(file_path)

    ClientFile.objects.filter(client=client_profile, name=filename).delete()

    return redirect("dashboard")
