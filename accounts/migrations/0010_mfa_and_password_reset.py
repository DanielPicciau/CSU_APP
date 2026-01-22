from django.db import migrations, models
import django.db.models.deletion
import core.fields


class Migration(migrations.Migration):

    dependencies = [
        ("accounts", "0009_encrypt_profile_fields"),
    ]

    operations = [
        migrations.CreateModel(
            name="UserMFA",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("secret", core.fields.EncryptedCharField(help_text="Base32-encoded TOTP secret", max_length=64)),
                ("enabled", models.BooleanField(default=False, help_text="Whether MFA is enabled for this user")),
                ("confirmed_at", models.DateTimeField(blank=True, help_text="When MFA was confirmed", null=True)),
                ("last_used_at", models.DateTimeField(blank=True, help_text="Last successful MFA verification", null=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("user", models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, related_name="mfa", to="accounts.user")),
            ],
            options={
                "verbose_name": "MFA configuration",
                "verbose_name_plural": "MFA configurations",
            },
        ),
        migrations.CreateModel(
            name="PasswordResetToken",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("token_hash", models.CharField(db_index=True, help_text="SHA256-based token hash", max_length=64)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("expires_at", models.DateTimeField()),
                ("used_at", models.DateTimeField(blank=True, null=True)),
                ("requested_ip", models.CharField(blank=True, default="", max_length=45)),
                ("requested_user_agent", models.CharField(blank=True, default="", max_length=200)),
                ("user", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="password_reset_tokens", to="accounts.user")),
            ],
            options={
                "verbose_name": "password reset token",
                "verbose_name_plural": "password reset tokens",
                "indexes": [
                    models.Index(fields=["user", "token_hash"], name="accounts_pa_user_id_6a1d8b_idx"),
                    models.Index(fields=["expires_at"], name="accounts_pa_expires_c9b9b7_idx"),
                ],
            },
        ),
    ]
